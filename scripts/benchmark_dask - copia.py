"""
Benchmark con Dask — dos configuraciones de workers y memoria
================================================================

Requisito del docente (punto 1.e): usar Dask en alguna parte del
proceso, evidenciando AL MENOS DOS configuraciones distintas de
workers y memoria por worker.

Qué hace este script:
  - Lee el Parquet particionado que ya generaste (data/parquet).
  - Calcula el % de atrasos por aerolínea/mes/año (el mismo tipo de
    agregación que ya corriste con DuckDB en la Unidad 2).
  - Corre ese cálculo DOS VECES, cada vez con un clúster local de Dask
    configurado distinto:
        Config A: 2 workers, 2 hilos cada uno, 2 GB de memoria c/u
        Config B: 4 workers, 1 hilo cada uno,  1 GB de memoria c/u
  - Mide el tiempo de cada configuración y las compara al final.

Ambas configuraciones usan el mismo total de "poder de cómputo"
(4 unidades), pero repartido distinto: Config A favorece procesos
grandes con varios hilos cada uno; Config B favorece muchos procesos
pequeños. Esa diferencia es justo lo que vale la pena discutir en el
documento final (cuál rindió mejor y por qué).

Antes de correrlo (ambiente conda "bigdata", en Anaconda Prompt):
    conda activate bigdata
    pip install "dask[complete]"

Mientras corre cada configuración, puedes abrir el link del dashboard
que imprime en consola (algo como http://127.0.0.1:8787) para ver en
vivo cómo se reparte el trabajo entre los workers — esa pantalla es
la captura que pegas como evidencia en el documento.
"""

import time
from pathlib import Path

import pandas as pd
import dask.dataframe as dd
from dask.distributed import Client, LocalCluster

CARPETA_PARQUET = Path("data/parquet")


def correr_analisis_dask(n_workers: int, threads_per_worker: int, memory_limit: str, etiqueta: str) -> dict:
    print(f"\n{'=' * 60}")
    print(f"Configuración: {etiqueta}")
    print(f"{'=' * 60}")

    cluster = LocalCluster(
        n_workers=n_workers,
        threads_per_worker=threads_per_worker,
        memory_limit=memory_limit,
    )
    client = Client(cluster)
    print(f"Dashboard (ábrelo en el navegador mientras corre): {client.dashboard_link}")

    inicio = time.time()

    ddf = dd.read_parquet(str(CARPETA_PARQUET))
    resumen = (
        ddf.groupby(["Year", "Month", "Reporting_Airline"])
        .agg(vuelos=("ArrDel15", "count"), atrasados=("ArrDel15", "sum"))
        .compute()
    )
    resumen["pct_atrasados"] = (resumen["atrasados"] / resumen["vuelos"] * 100).round(2)

    duracion = time.time() - inicio

    print(f"Tiempo total:     {duracion:.1f} segundos")
    print(f"Filas resultado:  {len(resumen):,}")

    client.close()
    cluster.close()

    return {
        "configuracion": etiqueta,
        "n_workers": n_workers,
        "threads_por_worker": threads_per_worker,
        "memoria_por_worker": memory_limit,
        "segundos": round(duracion, 1),
    }


if __name__ == "__main__":
    resultados = []

    resultados.append(correr_analisis_dask(
        n_workers=2,
        threads_per_worker=2,
        memory_limit="2GB",
        etiqueta="Config A — 2 workers x 2 hilos, 2GB cada uno",
    ))

    resultados.append(correr_analisis_dask(
        n_workers=4,
        threads_per_worker=1,
        memory_limit="1GB",
        etiqueta="Config B — 4 workers x 1 hilo, 1GB cada uno",
    ))

    print(f"\n{'=' * 60}")
    print("COMPARACIÓN FINAL")
    print(f"{'=' * 60}")
    tabla = pd.DataFrame(resultados)
    print(tabla.to_string(index=False))

    Path("data/resultados").mkdir(parents=True, exist_ok=True)
    tabla.to_csv("data/resultados/benchmark_dask.csv", index=False)
    print("\nGuardado en data/resultados/benchmark_dask.csv")
