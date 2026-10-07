"""
Sube a AWS RDS (PostgreSQL) SOLO las tablas agregadas de CO2.

No sube ZIP, ni CSV de BTS, ni Parquet por vuelo.

Es idempotente: si lo vuelves a correr, reemplaza las tablas. Sirve para
una base que permanece y también para recargar todo cuando AWS Academy
borra la sesión.

Credenciales: solo desde el archivo .env de la raíz del proyecto.
Hay un modo de prueba que no se conecta:

    conda activate bigdata
    python scripts/subir_resultados_aws.py --dry-run
    python scripts/subir_resultados_aws.py

La guía para crear la base está en docs/guia_aws_grafana.md.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.types import BigInteger, Float, Integer, Text

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import config

# CSV de resultados -> tabla en PostgreSQL. Nada de esta lista es un vuelo suelto.
TABLAS = {
    "resumen_global": {
        "csv": "resumen_global.csv",
        "tipos": {
            "anio": Integer(),
            "vuelos": BigInteger(),
            "horas_salida": Float(),
            "horas_llegada": Float(),
            "horas": Float(),
            "co2_t_bajo": Float(),
            "co2_t_alto": Float(),
        },
        "indices": [
            "CREATE INDEX IF NOT EXISTS idx_resumen_anio ON resumen_global (anio)",
        ],
    },
    "co2_aeropuerto_mes": {
        "csv": "co2_aeropuerto_mes.csv",
        "tipos": {
            "aeropuerto": Text(),
            "anio": Integer(),
            "mes": Integer(),
            "vuelos_salida": BigInteger(),
            "vuelos_llegada": BigInteger(),
            "vuelos": BigInteger(),
            "min_rodaje_salida": Float(),
            "min_rodaje_llegada": Float(),
            "horas_salida": Float(),
            "horas_llegada": Float(),
            "horas": Float(),
            "co2_t_bajo_salida": Float(),
            "co2_t_alto_salida": Float(),
            "co2_t_bajo_llegada": Float(),
            "co2_t_alto_llegada": Float(),
            "co2_t_bajo": Float(),
            "co2_t_alto": Float(),
        },
        "indices": [
            "CREATE INDEX IF NOT EXISTS idx_mes_aeropuerto ON co2_aeropuerto_mes (aeropuerto)",
            "CREATE INDEX IF NOT EXISTS idx_mes_periodo ON co2_aeropuerto_mes (anio, mes)",
        ],
    },
    "co2_aeropuerto_hora": {
        "csv": "co2_aeropuerto_hora.csv",
        "tipos": {
            "aeropuerto": Text(),
            "hora": Integer(),
            "vuelos": BigInteger(),
            "min_promedio_salida": Float(),
            "min_rodaje_salida": Float(),
            "co2_t_bajo": Float(),
            "co2_t_alto": Float(),
        },
        "indices": [
            "CREATE INDEX IF NOT EXISTS idx_hora_aeropuerto ON co2_aeropuerto_hora (aeropuerto, hora)",
        ],
    },
    "rodaje_clima": {
        "csv": "rodaje_clima.csv",
        "tipos": {
            "condicion": Text(),
            "vuelos": BigInteger(),
            "min_promedio_salida": Float(),
        },
        "indices": [],
    },
    "rodaje_clima_independiente": {
        "csv": "rodaje_clima_independiente.csv",
        "tipos": {
            "condicion": Text(),
            "vuelos": BigInteger(),
            "min_promedio_salida": Float(),
        },
        "indices": [],
    },
    "escenario_ahorro": {
        "csv": "escenario_ahorro.csv",
        "tipos": {
            "concepto": Text(),
            "detalle": Text(),
            "co2_t_bajo_actual": Float(),
            "co2_t_evitado": Float(),
            "co2_t_bajo_escenario": Float(),
        },
        "indices": [],
    },
    "benchmark_dask": {
        "csv": "benchmark_dask.csv",
        "tipos": None,
        "indices": [],
    },
}


def leer_csv(nombre: str) -> pd.DataFrame | None:
    ruta = config.CARPETA_RESULTADOS / nombre
    if not ruta.exists():
        print(f"  [falta] {ruta}")
        return None
    df = pd.read_csv(ruta)
    print(f"  [ok] {nombre}: {len(df):,} filas, columnas: {', '.join(df.columns)}")
    return df


def dry_run() -> int:
    print("Revisión de CSV, sin conectarse a AWS:\n")
    faltan = 0
    for nombre, info in TABLAS.items():
        df = leer_csv(info["csv"])
        if df is None:
            faltan += 1
            continue
        if info["tipos"] is not None:
            sobran = set(df.columns) - set(info["tipos"])
            ausentes = set(info["tipos"]) - set(df.columns)
            if sobran or ausentes:
                print(f"       columnas distintas. sobran={sorted(sobran)} faltan={sorted(ausentes)}")
                faltan += 1
    if faltan:
        print(f"\nHay {faltan} archivos por corregir antes de subir.")
        return 1
    print("\nLos CSV están listos. Falta solo el .env y la base en AWS.")
    return 0


def subir() -> None:
    load_dotenv(RAIZ / ".env")
    host = os.getenv("AWS_HOST")
    port = os.getenv("AWS_PORT", "5432")
    user = os.getenv("AWS_USER")
    password = os.getenv("AWS_PASSWORD")
    database = os.getenv("AWS_DATABASE", "postgres")

    if not all([host, user, password]):
        raise SystemExit(
            "Faltan AWS_HOST, AWS_USER o AWS_PASSWORD en el archivo .env. "
            "Copia .env.example a .env y rellénalo. No pegues la clave en el código."
        )

    engine = create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    )
    print("Conectando a la base (el host no se imprime completo a propósito)...")
    with engine.connect() as con:
        con.execute(text("SELECT 1"))
    print("Conexión lista.\n")

    with engine.begin() as con:
        for tabla, info in TABLAS.items():
            df = leer_csv(info["csv"])
            if df is None:
                continue
            df.to_sql(
                tabla,
                con,
                if_exists="replace",
                index=False,
                dtype=info["tipos"],
            )
            for sentencia in info["indices"]:
                con.execute(text(sentencia))
            total = con.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar()
            print(f"  tabla {tabla}: {total:,} filas")

    print("\nListo. En la base solo quedaron tablas de resultados.")
    print("Comprueba con:")
    print("  SELECT COUNT(*) FROM resumen_global;")
    print("  SELECT COUNT(*) FROM co2_aeropuerto_mes;")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sube resultados agregados a RDS")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Revisa los CSV y no abre conexión",
    )
    args = parser.parse_args()
    if args.dry_run:
        raise SystemExit(dry_run())
    subir()
