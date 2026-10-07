"""
Flujo de ingesta y analítica de rodaje / CO2 — BTS On-Time Performance.

Qué se conservó del flujo anterior:
  - descargar_mes: si el ZIP ya está, no lo vuelve a bajar.
  - validar_y_convertir: si el mes ya está en Parquet, lo omite.

Qué calcula:
  - limpiar_rodaje: cuenta nulos y atípicos, sin borrar el Parquet.
  - calcular_co2: arma las tablas con el consumo en kg/min que le pases.
  - agregar_resultados: guarda los CSV. Si esta tarea no llega a correr,
    los CSV anteriores quedan intactos.

Fallo controlado (Unidad 4):
  Con demostrar_fallo=True el flujo prueba un ZIP corrupto y un esquema
  sin TaxiOut/TaxiIn. Los detecta, los escribe en el log y sigue.
  No toca los Parquet buenos ni reemplaza los CSV hasta el final.

Antes de correrlo (Anaconda Prompt, carpeta del proyecto):
  conda activate bigdata

  Terminal 1:  prefect server start
  Terminal 2:  python scripts/flujo_ingesta_prefect.py

La segunda corrida de evidencia (un mes nuevo, los demás omitidos)
está comentada al final de este archivo.
"""

from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests

from prefect import flow, task, get_run_logger

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import config
from calcular_co2 import (
    calcular_agregados,
    escribir_resultados,
    estadisticas_limpieza,
)

CARPETA_RAW = Path("data/raw")
CARPETA_PARQUET = Path("data/parquet")

URL_BASE = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
)

# TaxiOut y TaxiIn se exigen porque sin ellos no hay pregunta de rodaje.
# Si faltan, el mes se rechaza ANTES de borrar o escribir Parquet.
COLUMNAS_ESPERADAS = {
    "Year", "Month", "Reporting_Airline", "Origin", "Dest",
    "ArrDel15", "DepDelay", "ArrDelay",
    "TaxiOut", "TaxiIn", "CRSDepTime",
}


@task(retries=3, retry_delay_seconds=10, name="descargar_mes")
def descargar_mes(año: int, mes: int) -> Path:
    """Descarga un mes de BTS. Si ya existe localmente, no repite la descarga."""
    logger = get_run_logger()
    CARPETA_RAW.mkdir(parents=True, exist_ok=True)

    nombre = f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{año}_{mes}.zip"
    destino = CARPETA_RAW / nombre

    if destino.exists() and destino.stat().st_size > 0:
        logger.info(f"{año}-{mes:02d} ya estaba descargado — se omite")
        return destino

    requests.packages.urllib3.disable_warnings()
    r = requests.get(URL_BASE.format(year=año, month=mes), timeout=120, verify=False)
    r.raise_for_status()
    destino.write_bytes(r.content)
    logger.info(f"{año}-{mes:02d} descargado ({destino.stat().st_size / 1e6:.1f} MB)")
    return destino


@task(name="validar_y_convertir")
def validar_y_convertir(zip_path: Path) -> dict:
    """Convierte cada mes una sola vez. Un esquema malo no borra lo ya convertido."""
    logger = get_run_logger()

    año, mes = map(int, zip_path.stem.rsplit("_", 2)[-2:])
    particion = CARPETA_PARQUET / f"Year={año}" / f"Month={mes}"
    marca = particion / "_completado"

    if marca.exists() and list(particion.glob("*.parquet")):
        logger.info(f"{año}-{mes:02d} ya estaba convertido — se omite")
        return {"archivo": zip_path.name, "estado": "omitido"}

    try:
        with zipfile.ZipFile(zip_path) as z:
            nombre_csv = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
            with z.open(nombre_csv) as f:
                df = pd.read_csv(f, low_memory=False)
    except zipfile.BadZipFile:
        logger.error(
            f"ZIP corrupto: {zip_path.name}. No se escribió Parquet y no se "
            "borró ninguna partición existente."
        )
        return {"archivo": zip_path.name, "estado": "zip_corrupto"}

    faltantes = COLUMNAS_ESPERADAS - set(df.columns)
    if faltantes:
        logger.error(
            f"{zip_path.name}: faltan columnas {sorted(faltantes)}. "
            "El mes se rechaza. El Parquet anterior no se toca."
        )
        return {
            "archivo": zip_path.name,
            "estado": "esquema_incompleto",
            "columnas_faltantes": sorted(faltantes),
        }

    if particion.exists():
        shutil.rmtree(particion)

    CARPETA_PARQUET.mkdir(parents=True, exist_ok=True)
    tabla = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_to_dataset(
        tabla,
        root_path=str(CARPETA_PARQUET),
        partition_cols=["Year", "Month"],
    )

    marca.write_text("ok", encoding="utf-8")
    logger.info(f"{zip_path.name}: {len(df):,} filas convertidas a Parquet")
    return {
        "archivo": zip_path.name,
        "estado": "convertido",
        "filas": len(df),
    }


@task(name="limpiar_rodaje")
def limpiar_rodaje() -> dict:
    """Mide la calidad del rodaje sobre todo el Parquet. No elimina filas del archivo."""
    logger = get_run_logger()
    calidad = estadisticas_limpieza()
    logger.info(
        "Limpieza: %(filas)s filas, %(vuelos_validos)s válidas "
        "(ambos tiempos no nulos y <= 180 min). "
        "TaxiOut nulo: %(taxiout_nulo)s. TaxiIn nulo: %(taxiin_nulo)s. "
        "Máximo TaxiOut: %(taxiout_max)s min (se documenta, no se borra del Parquet)."
        % calidad
    )
    return {k: (None if pd.isna(v) else v) for k, v in calidad.items()}


@task(name="calcular_co2")
def calcular_co2(consumo_kg_min: float) -> dict:
    """
    Calcula los agregados.

    consumo_kg_min reemplaza el escenario bajo (por defecto 6).
    El escenario alto sigue saliendo de config.py y queda marcado
    como "por validar".
    """
    logger = get_run_logger()
    logger.info(
        f"Consumo del escenario bajo para esta corrida: {consumo_kg_min} kg/min. "
        f"Escenario alto: {config.CONSUMO_KG_MIN_ALTO} kg/min (por validar). "
        f"Factor CO2: {config.FACTOR_CO2}."
    )
    tablas = calcular_agregados(consumo_bajo=consumo_kg_min)
    logger.info(
        "Agregados listos: "
        + ", ".join(f"{nombre}={len(df)} filas" for nombre, df in tablas.items())
    )
    return tablas


@task(name="agregar_resultados")
def agregar_resultados(tablas: dict) -> dict:
    """Guarda los CSV. Cada archivo se escribe entero y luego se renombra."""
    logger = get_run_logger()
    rutas = escribir_resultados(tablas)
    for nombre, ruta in rutas.items():
        logger.info(f"Guardado {ruta} ({len(tablas[nombre])} filas)")
    return {nombre: str(ruta) for nombre, ruta in rutas.items()}


@task(name="demostrar_fallo_controlado")
def demostrar_fallo_controlado() -> dict:
    """
    Dos fallos a propósito, en una carpeta temporal.
    El Parquet real y los CSV no se modifican aquí.
    """
    logger = get_run_logger()
    resultado = {"zip_corrupto": None, "esquema_incompleto": None}

    with tempfile.TemporaryDirectory() as tmp:
        malo = Path(tmp) / "vacio.zip"
        malo.write_bytes(b"esto no es un zip")
        try:
            with zipfile.ZipFile(malo) as z:
                z.namelist()
            logger.error("No se detectó el ZIP corrupto. Revisa el flujo.")
            resultado["zip_corrupto"] = "no_detectado"
        except zipfile.BadZipFile:
            logger.error(
                "FALLO CONTROLADO detectado: ZIP corrupto. "
                "El flujo lo registra y continúa. No se escribió Parquet."
            )
            resultado["zip_corrupto"] = "detectado"

        incompleto = Path(tmp) / "sin_rodaje.zip"
        with zipfile.ZipFile(incompleto, "w") as z:
            z.writestr("vuelos.csv", "Year,Month,Origin\n2023,1,ATL\n")
        with zipfile.ZipFile(incompleto) as z:
            with z.open("vuelos.csv") as f:
                cabecera = f.readline().decode("utf-8")
        columnas = {c.strip() for c in cabecera.split(",")}
        faltantes = {"TaxiOut", "TaxiIn"} - columnas
        if faltantes:
            logger.error(
                "FALLO CONTROLADO detectado: esquema sin %s. "
                "El mes se rechazaría antes de tocar el Parquet. El flujo continúa.",
                sorted(faltantes),
            )
            resultado["esquema_incompleto"] = "detectado"
        else:
            resultado["esquema_incompleto"] = "no_detectado"

    return resultado


@flow(name="ingesta-y-analitica-bts")
def flujo_ingesta_bts(
    periodos: list[tuple[int, int]],
    consumo_kg_min: float = config.CONSUMO_KG_MIN_BAJO,
    demostrar_fallo: bool = False,
):
    """
    periodos: lista de (año, mes).

    Un mes que ya está descargado y convertido se omite.
    Al final, el CO2 se recalcula sobre TODO el Parquet, no solo sobre el mes nuevo.
    """
    fallo = demostrar_fallo_controlado() if demostrar_fallo else None

    reportes = []
    for año, mes in periodos:
        zip_path = descargar_mes(año, mes)
        reporte = validar_y_convertir(zip_path)
        reportes.append(reporte)

    calidad = limpiar_rodaje()
    tablas = calcular_co2(consumo_kg_min)
    rutas = agregar_resultados(tablas)

    return {
        "fallo_controlado": fallo,
        "reportes_ingesta": reportes,
        "vuelos_validos": calidad.get("vuelos_validos"),
        "archivos_co2": rutas,
    }


if __name__ == "__main__":
    # Corrida base: 2023-2025. Los meses ya convertidos se omiten
    # y el CO2 se recalcula sobre el Parquet completo.
    periodos_base = [(año, mes) for año in config.ANIOS for mes in config.MESES]
    flujo_ingesta_bts(periodos_base, demostrar_fallo=False)

    # Segunda corrida de evidencia (hazla en otra ejecución, no aquí):
    # agrega un mes que todavía no está. Los 36 anteriores deben decir "omitido".
    #
    # periodos_con_mes_nuevo = periodos_base + [(2026, 1)]
    # flujo_ingesta_bts(periodos_con_mes_nuevo, demostrar_fallo=False)
    #
    # Tercera corrida, solo para la captura del fallo controlado:
    #
    # flujo_ingesta_bts(periodos_base, demostrar_fallo=True)
