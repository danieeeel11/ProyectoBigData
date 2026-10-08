"""
Parámetros del proyecto de rodaje y CO2.

Cambia los números aquí. Los scripts leen este archivo, así que no hace
falta buscar el 6 o el 3.16 dentro del código.

El escenario alto (12 kg por minuto) está POR VALIDAR con la base de
emisiones de motores de OACI/EASA. No es una cifra cerrada.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent

CARPETA_RAW = RAIZ / "data" / "raw"
CARPETA_PARQUET = RAIZ / "data" / "parquet"
CARPETA_RESULTADOS = RAIZ / "data" / "resultados"
RUTA_CLIMA = RAIZ / "data" / "clima" / "clima_aeropuertos.csv"

# kg de combustible por minuto de rodaje, con los motores encendidos.
CONSUMO_KG_MIN_BAJO = 6.0
CONSUMO_KG_MIN_ALTO = 12.0  # POR VALIDAR

# kg de CO2 por cada kg de combustible. OACI usa 3.16; EUROCONTROL usa 3.15.
FACTOR_CO2 = 3.16

# Por encima de esto el tiempo se considera atípico y no entra en los totales.
# El valor original se conserva en los datos; aquí solo se excluye del cálculo.
TAXI_MAX_MIN = 180

ANIOS = (2023, 2024, 2025)
MESES = tuple(range(1, 13))

# Umbrales del cruce con clima.
LLUVIA_FUERTE_MM = 5.0
VIENTO_FUERTE_KMH = 40.0

# Un aeropuerto entra en el ranking de "rodaje lento" si tiene más vuelos que esto.
MIN_VUELOS_RANKING = 50_000


def patron_parquet() -> str:
    """Ruta que DuckDB usa para leer todas las particiones."""
    return str(CARPETA_PARQUET / "**" / "*.parquet").replace("\\", "/")
