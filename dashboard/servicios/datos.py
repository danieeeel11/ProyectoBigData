"""Datos del dashboard.

Lee las tablas que ya calculó y verificó scripts/calcular_co2.py en
data/resultados/. No vuelve a leer el Parquet, así que el dashboard corre
en cualquier computador que tenga el repo, aunque no tenga los 664 MB.
"""
from functools import lru_cache
from pathlib import Path
import sys

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
import config  # noqa: E402  (config.py del proyecto)

R = config.CARPETA_RESULTADOS


@lru_cache
def por_mes() -> pd.DataFrame:
    df = pd.read_csv(R / "co2_aeropuerto_mes.csv")
    df["periodo"] = pd.to_datetime(dict(year=df.anio, month=df.mes, day=1))
    return df


@lru_cache
def por_hora() -> pd.DataFrame:
    return pd.read_csv(R / "co2_aeropuerto_hora.csv")


@lru_cache
def clima() -> pd.DataFrame:
    return pd.read_csv(R / "rodaje_clima.csv")


@lru_cache
def ahorro() -> pd.DataFrame:
    return pd.read_csv(R / "escenario_ahorro.csv")


def columnas_co2(escenario: str, tipos: list[str]) -> list[str]:
    """Columnas de CO2 según el escenario (bajo/alto) y el tipo de rodaje."""
    return [f"co2_t_{escenario}_{t}" for t in tipos]


def filtrar_mes(anios, tipos, escenario) -> pd.DataFrame:
    df = por_mes()
    df = df[df.anio.isin(anios)].copy()
    df["co2_t"] = df[columnas_co2(escenario, tipos)].sum(axis=1)
    df["horas_sel"] = df[[f"horas_{t}" for t in tipos]].sum(axis=1)
    df["vuelos_sel"] = df[[f"vuelos_{t}" for t in tipos]].sum(axis=1)
    return df


def formato(x, decimales=0) -> str:
    texto = f"{x:,.{decimales}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")
