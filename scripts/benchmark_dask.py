# ============================================================
# BENCHMARK CON DASK
# Proyecto Big Data - BTS On-Time Performance
# ============================================================

from pathlib import Path
import time

import pandas as pd
import dask.dataframe as dd
from dask.distributed import Client, LocalCluster


# ============================================================
# 1. RUTAS DEL PROYECTO
# ============================================================

CARPETA_PARQUET = Path("data/parquet")
CARPETA_RESULTADOS = Path("data/resultados")

# Creamos la carpeta de resultados si todavía no existe
CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. FUNCIÓN QUE EJECUTA UNA CONFIGURACIÓN DE DASK
# ============================================================

def ejecutar_benchmark(
    nombre_configuracion,
    n_workers,
    threads_por_worker,
    memoria_por_worker
):
    """
    Ejecuta la misma consulta utilizando una configuración específica
    de Dask y mide cuánto tiempo tarda.

    Parámetros:
    - nombre_configuracion: nombre que aparecerá en consola.
    - n_workers: cantidad de procesos de Dask.
    - threads_por_worker: cantidad de hilos de cada worker.
    - memoria_por_worker: memoria disponible para cada worker.
    """

    print("\n" + "=" * 60)
    print(f"Configuración: {nombre_configuracion}")
    print("=" * 60)

    # --------------------------------------------------------
    # 3. CREAR EL CLUSTER LOCAL DE DASK
    # --------------------------------------------------------

    cluster = LocalCluster(
        n_workers=n_workers,
        threads_per_worker=threads_por_worker,
        memory_limit=memoria_por_worker,
        dashboard_address=":8787"
    )

    # El Client conecta Python con el cluster que acabamos de crear
    client = Client(cluster)

    print(
        f"\nDashboard de Dask: {client.dashboard_link}"
    )

    # --------------------------------------------------------
    # PAUSA 1:
    # Te permite abrir el Dashboard ANTES de que comience el cálculo.
    # --------------------------------------------------------

    print("\nIMPORTANTE:")
    print("1. Copia el enlace del Dashboard.")
    print("2. Ábrelo en Chrome.")
    print("3. Deja el navegador abierto.")
    print("4. Regresa a esta terminal.")

    input(
        "\nCuando tengas abierto el Dashboard, "
        "presiona ENTER para comenzar el benchmark..."
    )

    # --------------------------------------------------------
    # 4. LEER LOS ARCHIVOS PARQUET
    # --------------------------------------------------------

    # Dask NO carga todo inmediatamente.
    # Primero construye un plan de trabajo.
    df = dd.read_parquet(
        str(CARPETA_PARQUET),
        engine="pyarrow"
    )

    # Solamente dejamos las columnas necesarias
    columnas = [
        "Year",
        "Month",
        "Reporting_Airline",
        "ArrDel15"
    ]

    df = df[columnas]

    # --------------------------------------------------------
    # 5. INICIAR CRONÓMETRO
    # --------------------------------------------------------

    inicio = time.perf_counter()

    # --------------------------------------------------------
    # 6. ANALÍTICA DISTRIBUIDA
    # --------------------------------------------------------

    # Primero agrupamos por:
    # año, mes y aerolínea.
    #
    # Después calculamos:
    # - cantidad de vuelos
    # - cantidad de vuelos atrasados

    resumen = (
        df.groupby(
            ["Year", "Month", "Reporting_Airline"]
        )
        .agg(
            {
                "ArrDel15": ["count", "sum"]
            }
        )
    )

    # --------------------------------------------------------
    # 7. .compute()
    # --------------------------------------------------------

    # Esta es una de las líneas más importantes.
    #
    # Hasta aquí Dask solamente había preparado el trabajo.
    # .compute() hace que los workers empiecen realmente
    # a procesar los archivos Parquet.
    #
    # EN ESTE MOMENTO puedes mirar el Dashboard.

    resultado = resumen.compute()

    # --------------------------------------------------------
    # 8. TERMINAR CRONÓMETRO
    # --------------------------------------------------------

    fin = time.perf_counter()

    segundos = round(fin - inicio, 1)

    # Dejamos el DataFrame nuevamente como una tabla normal
    resultado = resultado.reset_index()

    # Cambiamos los nombres de las columnas
    resultado.columns = [
        "Year",
        "Month",
        "Reporting_Airline",
        "vuelos",
        "vuelos_atrasados"
    ]

    # Calculamos el porcentaje de vuelos atrasados
    resultado["pct_atrasados"] = (
        100
        * resultado["vuelos_atrasados"]
        / resultado["vuelos"]
    ).round(2)

    print("\nProceso terminado.")
    print(f"Tiempo total:      {segundos} segundos")
    print(f"Filas resultado:   {len(resultado)}")

    # --------------------------------------------------------
    # PAUSA 2:
    # El cluster NO se cierra todavía.
    #
    # Aquí puedes tomar tu captura tranquilamente.
    # --------------------------------------------------------

    print("\n" + "-" * 60)
    print("EL DASHBOARD SIGUE ACTIVO")
    print("-" * 60)

    print("\nAhora:")
    print("1. Vuelve al navegador.")
    print("2. Toma la captura del Dashboard.")
    print("3. Guarda la imagen.")
    print("4. Regresa a Anaconda Prompt.")

    input(
        "\nCuando ya tengas la captura, "
        "presiona ENTER para cerrar esta configuración..."
    )

    # --------------------------------------------------------
    # 9. CERRAR DASK ORDENADAMENTE
    # --------------------------------------------------------

    # Primero cerramos el cliente
    client.close()

    # Después cerramos el cluster
    cluster.close()

    # --------------------------------------------------------
    # 10. DEVOLVER RESULTADO DEL BENCHMARK
    # --------------------------------------------------------

    return {
        "configuracion": nombre_configuracion,
        "n_workers": n_workers,
        "threads_por_worker": threads_por_worker,
        "memoria_por_worker": memoria_por_worker,
        "segundos": segundos,
        "filas_resultado": len(resultado)
    }


# ============================================================
# 11. PROGRAMA PRINCIPAL
# ============================================================

if __name__ == "__main__":

    resultados_benchmark = []

    # ========================================================
    # CONFIGURACIÓN A
    # ========================================================

    resultado_a = ejecutar_benchmark(
        nombre_configuracion="Config A — 2 workers x 2 hilos, 2GB cada uno",
        n_workers=2,
        threads_por_worker=2,
        memoria_por_worker="2GB"
    )

    resultados_benchmark.append(resultado_a)

    # ========================================================
    # CONFIGURACIÓN B
    # ========================================================

    resultado_b = ejecutar_benchmark(
        nombre_configuracion="Config B — 4 workers x 1 hilo, 1GB cada uno",
        n_workers=4,
        threads_por_worker=1,
        memoria_por_worker="1GB"
    )

    resultados_benchmark.append(resultado_b)

    # ========================================================
    # 12. TABLA FINAL
    # ========================================================

    tabla_resultados = pd.DataFrame(resultados_benchmark)

    print("\n")
    print("=" * 60)
    print("COMPARACIÓN FINAL")
    print("=" * 60)

    print(
        tabla_resultados[
            [
                "configuracion",
                "n_workers",
                "threads_por_worker",
                "memoria_por_worker",
                "segundos",
                "filas_resultado"
            ]
        ].to_string(index=False)
    )

    # ========================================================
    # 13. GUARDAR RESULTADOS EN CSV
    # ========================================================

    archivo_salida = (
        CARPETA_RESULTADOS
        / "benchmark_dask.csv"
    )

    tabla_resultados.to_csv(
        archivo_salida,
        index=False
    )

    print(
        f"\nResultados guardados en: {archivo_salida}"
    )

    print("\nBenchmark finalizado correctamente.")