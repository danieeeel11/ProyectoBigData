"""
Flujo de ingesta y analítica recurrente — BTS On-Time Performance
==================================================================

Requisito del docente (punto 1.d): un flujo con Prefect que, si llega
un conjunto de datos similar o adicional, transforme y recalcule la
analítica de nuevo, sin reescribir el pipeline.

Cómo cumple esto este script:
  - Cada mes se identifica por (año, mes). Si ya fue descargado y
    convertido, el flujo lo detecta y lo omite (idempotente).
  - Para procesar datos nuevos, se vuelve a llamar el flujo con la
    lista de periodos AMPLIADA (ver el bloque `if __name__ == "__main__"`
    al final) — no hay que tocar el código de las tareas.
  - El último paso del flujo siempre recalcula la analítica agregada
    sobre TODO lo que haya en /data/parquet, así que el resultado
    queda actualizado automáticamente con los datos viejos + nuevos.

Antes de correrlo (en el ambiente conda "bigdata"):
    conda activate bigdata
    pip install prefect duckdb pyarrow requests

Para ver el historial de corridas (la evidencia visual que pide el docente):
    Terminal 1:  prefect server start        (deja esto corriendo, abre localhost:4200)
    Terminal 2:  python scripts/flujo_ingesta_prefect.py
"""

from pathlib import Path
import shutil
import zipfile

import requests
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import duckdb

from prefect import flow, task, get_run_logger

CARPETA_RAW = Path("data/raw")
CARPETA_PARQUET = Path("data/parquet")
CARPETA_RESULTADOS = Path("data/resultados")

URL_BASE = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
)

COLUMNAS_ESPERADAS = {
    "Year", "Month", "Reporting_Airline", "Origin", "Dest",
    "ArrDel15", "DepDelay", "ArrDelay",
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
    """Convierte cada mes una sola vez y permite retomar una ejecución interrumpida."""
    logger = get_run_logger()

    año, mes = map(int, zip_path.stem.rsplit("_", 2)[-2:])
    particion = CARPETA_PARQUET / f"Year={año}" / f"Month={mes}"
    marca = particion / "_completado"

    if marca.exists() and list(particion.glob("*.parquet")):
        logger.info(f"{año}-{mes:02d} ya estaba convertido — se omite")
        return {"archivo": zip_path.name, "estado": "omitido"}

    # Si una ejecución se interrumpió antes de terminar este mes,
    # se reconstruye únicamente esa partición.
    if particion.exists():
        shutil.rmtree(particion)

    with zipfile.ZipFile(zip_path) as z:
        nombre_csv = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        with z.open(nombre_csv) as f:
            df = pd.read_csv(f, low_memory=False)

    faltantes = COLUMNAS_ESPERADAS - set(df.columns)
    if faltantes:
        logger.warning(f"{zip_path.name}: faltan columnas esperadas {sorted(faltantes)}")

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
        "filas": len(df),
        "columnas_faltantes": sorted(faltantes),
    }


@task(name="recalcular_analitica")
def recalcular_analitica() -> pd.DataFrame:
    """Recalcula el % de atrasos por aerolínea/mes sobre TODO el Parquet disponible."""
    logger = get_run_logger()
    CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    resumen = con.execute(f"""
        SELECT
            Year, Month, Reporting_Airline,
            COUNT(*) AS vuelos,
            ROUND(100.0 * SUM(CASE WHEN ArrDel15 = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_atrasados
        FROM parquet_scan('{CARPETA_PARQUET}/**/*.parquet')
        GROUP BY Year, Month, Reporting_Airline
        ORDER BY Year, Month, Reporting_Airline
    """).fetchdf()

    salida = CARPETA_RESULTADOS / "resumen_atrasos_por_aerolinea_mes.csv"
    resumen.to_csv(salida, index=False)
    logger.info(f"Analítica recalculada: {len(resumen)} filas guardadas en {salida}")
    return resumen


@flow(name="ingesta-y-analitica-bts")
def flujo_ingesta_bts(periodos: list[tuple[int, int]]):
    """
    periodos: lista de tuplas (año, mes) a procesar.

    Para incorporar datos nuevos (un mes que se acaba de publicar, o un
    año adicional), se vuelve a llamar este flujo con la lista ampliada.
    Los periodos ya procesados se detectan y se omiten; la analítica del
    final siempre se recalcula sobre el total acumulado.
    """
    reportes = []
    for año, mes in periodos:
        zip_path = descargar_mes(año, mes)
        reporte = validar_y_convertir(zip_path)
        reportes.append(reporte)

    resumen = recalcular_analitica()
    return {"reportes_ingesta": reportes, "filas_resumen_analitica": len(resumen)}


if __name__ == "__main__":
    # Corrida base: 2023-2025 completo.
    periodos_base = [(año, mes) for año in [2023, 2024, 2025] for mes in range(1, 13)]
    flujo_ingesta_bts(periodos_base)

    # Cuando llegue un mes nuevo (ej. BTS publica enero 2026), agregarlo aquí
    # y volver a correr el script — no hace falta tocar nada más:
    #
    # periodos_actualizados = periodos_base + [(2026, 1)]
    # flujo_ingesta_bts(periodos_actualizados)
