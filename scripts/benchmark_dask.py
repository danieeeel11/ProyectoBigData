"""
Benchmark de Dask: CO2 de rodaje por aeropuerto, hora, mes.

Hace la misma agregación con al menos dos configuraciones de workers,
hilos y memoria. Las sumas de CO2 tienen que coincidir entre sí y con
DuckDB. Si no coinciden, el script se detiene: no se compara velocidad
de dos resultados distintos.

La máquina de referencia tiene 12 núcleos y unos 16 GB de RAM.
La configuración C (4 workers x 2 GB) solo corre si hay al menos 8 GB
libres, para no dejar el equipo sin memoria.

Uso (Anaconda Prompt, carpeta del proyecto):
    conda activate bigdata
    python scripts/benchmark_dask.py

Para tomar capturas del dashboard, agrega --pausa. El script espera
a que pulses ENTER antes y después de cada configuración.

El CSV anterior (enfoque de atrasos, 6,6 s y 12,9 s) quedó guardado en
data/resultados/benchmark_dask_atrasos.csv. Este script vuelve a escribir
data/resultados/benchmark_dask.csv con el cálculo de CO2.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path

import duckdb
import pandas as pd
import psutil
from dask.distributed import Client, LocalCluster

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import config

CARPETA_PARQUET = config.CARPETA_PARQUET
CARPETA_RESULTADOS = config.CARPETA_RESULTADOS


def memoria_arbol_mb() -> float:
    """RAM del proceso de Python y de los workers que haya lanzado."""
    yo = psutil.Process()
    total = 0
    procesos = [yo]
    try:
        procesos.extend(yo.children(recursive=True))
    except psutil.Error:
        pass
    for proceso in procesos:
        try:
            total += proceso.memory_info().rss
        except psutil.Error:
            continue
    return total / (1024 * 1024)


def suma_co2_duckdb() -> tuple[float, int]:
    """La misma cuenta, en DuckDB, para comprobar que Dask no cambió el resultado."""
    tope = config.TAXI_MAX_MIN
    factor = config.CONSUMO_KG_MIN_BAJO * config.FACTOR_CO2 / 1000.0
    con = duckdb.connect()
    fila = con.execute(
        f"""
        WITH base AS (
            SELECT
                Origin,
                Year,
                Month,
                CASE
                    WHEN CRSDepTime = 2400 THEN 0
                    WHEN CRSDepTime BETWEEN 0 AND 2359 THEN CRSDepTime // 100
                    ELSE NULL
                END AS hora,
                TaxiOut
            FROM read_parquet('{config.patron_parquet()}', hive_partitioning = true)
            WHERE TaxiOut IS NOT NULL AND TaxiOut <= {tope}
        )
        SELECT
            COUNT(*)::BIGINT AS grupos,
            SUM(minutos) * {factor} AS co2_t_bajo
        FROM (
            SELECT SUM(TaxiOut) AS minutos
            FROM base
            WHERE hora IS NOT NULL
            GROUP BY Origin, Year, Month, hora
        )
        """
    ).fetchone()
    con.close()
    return float(fila[1]), int(fila[0])


def ejecutar_benchmark(
    nombre_configuracion: str,
    n_workers: int,
    threads_por_worker: int,
    memoria_por_worker: str,
    pausa: bool,
) -> dict:
    print("\n" + "=" * 60)
    print(f"Configuración: {nombre_configuracion}")
    print("=" * 60)

    cluster = LocalCluster(
        n_workers=n_workers,
        threads_per_worker=threads_por_worker,
        memory_limit=memoria_por_worker,
        dashboard_address=":8787",
    )
    client = Client(cluster)
    print(f"\nDashboard de Dask: {client.dashboard_link}")

    if pausa:
        print("\nAbre ese enlace en el navegador y déjalo visible.")
        input("Cuando lo tengas abierto, presiona ENTER para calcular...")

    import dask.dataframe as dd

    df = dd.read_parquet(
        str(CARPETA_PARQUET),
        engine="pyarrow",
        columns=["Origin", "Year", "Month", "CRSDepTime", "TaxiOut"],
    )
    tope = config.TAXI_MAX_MIN
    df = df[df["TaxiOut"].notnull() & (df["TaxiOut"] <= tope)]
    hora = (df["CRSDepTime"] // 100).astype("Int64")
    hora = hora.mask(df["CRSDepTime"] == 2400, 0)
    df = df.assign(hora=hora)
    df = df[df["hora"].notnull() & (df["CRSDepTime"] >= 0) & (df["CRSDepTime"] <= 2400)]

    resumen = df.groupby(["Origin", "Year", "Month", "hora"])["TaxiOut"].agg(["sum", "count"])

    pico = {"mb": 0.0}
    parar = threading.Event()

    def vigilar():
        while not parar.is_set():
            pico["mb"] = max(pico["mb"], memoria_arbol_mb())
            parar.wait(0.25)

    hilo = threading.Thread(target=vigilar, daemon=True)
    hilo.start()
    inicio = time.perf_counter()
    resultado = resumen.compute()
    segundos = round(time.perf_counter() - inicio, 1)
    parar.set()
    hilo.join(timeout=1)

    resultado = resultado.reset_index()
    resultado.columns = [
        "aeropuerto", "anio", "mes", "hora", "min_rodaje_salida", "vuelos",
    ]
    factor = config.CONSUMO_KG_MIN_BAJO * config.FACTOR_CO2 / 1000.0
    suma_co2 = float(resultado["min_rodaje_salida"].sum() * factor)

    print(f"Tiempo:            {segundos} s")
    print(f"Filas resultado:   {len(resultado)}")
    print(f"CO2 escenario bajo:{suma_co2:,.1f} t")
    print(f"Memoria observada: {pico['mb']:,.0f} MB")

    if pausa:
        print("\nEl dashboard sigue abierto. Toma la captura ahora.")
        input("Cuando tengas la captura, presiona ENTER para cerrar esta configuración...")

    client.close()
    cluster.close()

    return {
        "configuracion": nombre_configuracion,
        "workers": n_workers,
        "hilos": threads_por_worker,
        "memoria_por_worker": memoria_por_worker,
        "segundos": segundos,
        "pico_memoria_mb": round(pico["mb"], 1),
        "filas_resultado": len(resultado),
        "suma_co2_t_bajo": round(suma_co2, 3),
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark Dask del CO2 de rodaje")
    parser.add_argument(
        "--pausa",
        action="store_true",
        help="Espera ENTER para que puedas capturar el dashboard",
    )
    args = parser.parse_args()

    print(f"Núcleos lógicos: {os.cpu_count()}")
    libre_gb = psutil.virtual_memory().available / 1e9
    print(f"RAM libre ahora: {libre_gb:.1f} GB")

    CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    referencia, grupos_duck = suma_co2_duckdb()
    print(f"Referencia DuckDB: {referencia:,.1f} t de CO2 en {grupos_duck} grupos")

    configuraciones = [
        ("Config A — 2 workers x 2 hilos, 2GB cada uno", 2, 2, "2GB"),
        ("Config B — 4 workers x 1 hilo, 1GB cada uno", 4, 1, "1GB"),
    ]
    if libre_gb >= 8:
        configuraciones.append(
            ("Config C — 4 workers x 2 hilos, 2GB cada uno", 4, 2, "2GB")
        )
    else:
        print(
            "\nConfig C no se corre: pide unos 8 GB libres y ahora hay "
            f"{libre_gb:.1f} GB. Con A y B ya se cumplen las dos configuraciones."
        )

    filas = []
    for nombre, workers, hilos, memoria in configuraciones:
        filas.append(ejecutar_benchmark(nombre, workers, hilos, memoria, args.pausa))

    tabla = pd.DataFrame(filas)
    sumas = tabla["suma_co2_t_bajo"].round(1)
    if sumas.nunique() != 1:
        raise SystemExit(
            "Las configuraciones de Dask no dieron el mismo CO2.\n" + tabla.to_string(index=False)
        )
    if abs(float(sumas.iloc[0]) - round(referencia, 1)) > 1:
        raise SystemExit(
            f"Dask ({sumas.iloc[0]} t) no coincide con DuckDB ({referencia:.1f} t)."
        )

    destino = CARPETA_RESULTADOS / "benchmark_dask.csv"
    tabla.to_csv(destino, index=False)

    print("\n" + "=" * 60)
    print("COMPARACIÓN FINAL — el CO2 coincide en todas")
    print("=" * 60)
    print(tabla.to_string(index=False))
    print(f"\nGuardado en {destino}")
    print("Misma suma de CO2 que DuckDB: sí.")


if __name__ == "__main__":
    main()
