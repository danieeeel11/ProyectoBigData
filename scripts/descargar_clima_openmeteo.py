"""
Enriquecimiento con clima — Open-Meteo
======================================

Objetivo:
Complementar el dataset BTS con información meteorológica diaria
para los 20 aeropuertos de origen seleccionados.

Importante:
- Este script NO descarga clima por hora.
- Descarga clima agregado por día.
- Por eso sirve como información contextual para analizar si los días
  con más lluvia, nieve o viento presentan diferencias en los atrasos.
- No debe interpretarse como el clima exacto en el momento de salida
  de cada vuelo.

Periodo:
2023-01-01 a 2025-12-31

Salida:
data/clima/clima_aeropuertos.csv

Antes de ejecutarlo:

    conda activate bigdata
    pip install requests pandas

Luego:

    python scripts/descargar_clima_openmeteo.py
"""

from pathlib import Path
import time

import pandas as pd
import requests


# ============================================================
# 1. CONFIGURACIÓN GENERAL
# ============================================================

FECHA_INICIO = "2023-01-01"
FECHA_FIN = "2025-12-31"

CARPETA_SALIDA = Path("data/clima")
ARCHIVO_SALIDA = CARPETA_SALIDA / "clima_aeropuertos.csv"

CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. AEROPUERTOS
# ============================================================

# Coordenadas aproximadas de los 20 aeropuertos seleccionados.
#
# Nota:
# Estos aeropuertos deben corresponder a los principales aeropuertos
# de origen identificados previamente en el EDA de BTS.
#
# Formato:
# "IATA": (latitud, longitud)

AEROPUERTOS = {
    "ATL": (33.6407, -84.4277),
    "DFW": (32.8998, -97.0403),
    "DEN": (39.8561, -104.6737),
    "ORD": (41.9742, -87.9073),
    "LAX": (33.9416, -118.4085),
    "JFK": (40.6413, -73.7781),
    "LAS": (36.0840, -115.1537),
    "MCO": (28.4312, -81.3081),
    "CLT": (35.2144, -80.9473),
    "MIA": (25.7959, -80.2870),
    "SEA": (47.4502, -122.3088),
    "EWR": (40.6895, -74.1745),
    "SFO": (37.6213, -122.3790),
    "PHX": (33.4352, -112.0101),
    "IAH": (29.9902, -95.3368),
    "BOS": (42.3656, -71.0096),
    "FLL": (26.0726, -80.1527),
    "MSP": (44.8848, -93.2223),
    "LGA": (40.7769, -73.8740),
    "DTW": (42.2162, -83.3554),
}


# ============================================================
# 3. FUNCIÓN PARA DESCARGAR EL CLIMA DE UN AEROPUERTO
# ============================================================

def descargar_clima(iata: str, lat: float, lon: float) -> pd.DataFrame:
    """
    Descarga información meteorológica diaria de Open-Meteo
    para un aeropuerto específico.

    Variables:
    - precipitation_sum:
        precipitación total diaria en mm.

    - snowfall_sum:
        nieve acumulada diaria.

    - wind_speed_10m_max:
        velocidad máxima diaria del viento a 10 metros.

    - temperature_2m_mean:
        temperatura media diaria a 2 metros.

    La zona horaria se determina automáticamente a partir
    de las coordenadas del aeropuerto.
    """

    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": FECHA_INICIO,
        "end_date": FECHA_FIN,
        "daily": (
            "precipitation_sum,"
            "snowfall_sum,"
            "wind_speed_10m_max,"
            "temperature_2m_mean"
        ),

        # IMPORTANTE:
        # Open-Meteo determina automáticamente la zona horaria
        # correspondiente a las coordenadas.
        "timezone": "auto",
    }

    print(f"Descargando clima de {iata}...")

    try:
        respuesta = requests.get(
            url,
            params=params,
            timeout=60
        )

        respuesta.raise_for_status()

    except requests.RequestException as error:
        print(f"ERROR descargando {iata}: {error}")
        return pd.DataFrame()

    datos_json = respuesta.json()

    if "daily" not in datos_json:
        print(f"ERROR: Open-Meteo no devolvió datos diarios para {iata}")
        return pd.DataFrame()

    datos = datos_json["daily"]

    # Validación mínima:
    # verificamos que existan las fechas.
    if "time" not in datos:
        print(f"ERROR: no se encontraron fechas para {iata}")
        return pd.DataFrame()

    df = pd.DataFrame({
        "Origin": iata,
        "Fecha": datos.get("time"),
        "precipitacion_mm": datos.get("precipitation_sum"),
        "nieve_cm": datos.get("snowfall_sum"),
        "viento_max_kmh": datos.get("wind_speed_10m_max"),
        "temp_media_c": datos.get("temperature_2m_mean"),
    })

    # Convertimos Fecha explícitamente a formato fecha.
    df["Fecha"] = pd.to_datetime(
        df["Fecha"],
        errors="coerce"
    )

    # Eliminamos filas donde la fecha no haya podido interpretarse.
    df = df.dropna(subset=["Fecha"])

    # La dejamos nuevamente como YYYY-MM-DD,
    # compatible con FlightDate de BTS para el JOIN.
    df["Fecha"] = df["Fecha"].dt.strftime("%Y-%m-%d")

    print(
        f"  ✓ {iata}: {len(df):,} días descargados"
    )

    return df


# ============================================================
# 4. DESCARGAR TODOS LOS AEROPUERTOS
# ============================================================

def main():

    print("=" * 60)
    print("DESCARGA DE CLIMA HISTÓRICO — OPEN-METEO")
    print("=" * 60)

    print(f"Periodo: {FECHA_INICIO} a {FECHA_FIN}")
    print(f"Aeropuertos: {len(AEROPUERTOS)}")
    print()

    resultados = []

    for iata, (lat, lon) in AEROPUERTOS.items():

        df_clima = descargar_clima(
            iata=iata,
            lat=lat,
            lon=lon
        )

        if not df_clima.empty:
            resultados.append(df_clima)

        # Pequeña pausa para no hacer solicitudes
        # demasiado seguidas a la API pública.
        time.sleep(1)

    # ========================================================
    # 5. VALIDAR QUE SE HAYAN DESCARGADO DATOS
    # ========================================================

    if not resultados:
        print()
        print("No se pudo descargar información meteorológica.")
        print("No se generará archivo de salida.")
        return

    # ========================================================
    # 6. UNIR LOS RESULTADOS
    # ========================================================

    clima = pd.concat(
        resultados,
        ignore_index=True
    )

    # ========================================================
    # 7. VERIFICACIONES BÁSICAS
    # ========================================================

    print()
    print("=" * 60)
    print("RESUMEN DE LA DESCARGA")
    print("=" * 60)

    print(f"Filas totales: {len(clima):,}")

    print(
        f"Aeropuertos descargados: "
        f"{clima['Origin'].nunique()}"
    )

    print(
        f"Fecha mínima: "
        f"{clima['Fecha'].min()}"
    )

    print(
        f"Fecha máxima: "
        f"{clima['Fecha'].max()}"
    )

    # Revisamos posibles duplicados por aeropuerto y fecha.
    duplicados = clima.duplicated(
        subset=["Origin", "Fecha"]
    ).sum()

    print(
        f"Duplicados Origin + Fecha: "
        f"{duplicados}"
    )

    # Si hubiera duplicados, los eliminamos.
    if duplicados > 0:
        clima = clima.drop_duplicates(
            subset=["Origin", "Fecha"]
        )

    # ========================================================
    # 8. GUARDAR CSV
    # ========================================================

    clima.to_csv(
        ARCHIVO_SALIDA,
        index=False
    )

    print()
    print(
        f"✓ Archivo guardado en:"
        f" {ARCHIVO_SALIDA}"
    )

    print()
    print(
        "Este archivo contiene clima DIARIO. "
        "Se utilizará como información contextual "
        "para analizar asociaciones con los atrasos."
    )


# ============================================================
# 9. EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    main()