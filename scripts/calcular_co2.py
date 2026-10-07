"""
Combustible y CO2 del rodaje en tierra — BTS 2023-2025.

Lee el Parquet completo (no una muestra), limpia los tiempos de rodaje
y guarda solo tablas agregadas en data/resultados/.

Regla de atribución:
  - TaxiOut se cuenta en el aeropuerto de ORIGEN (rodaje de salida).
  - TaxiIn se cuenta en el aeropuerto de DESTINO (rodaje de llegada).

Regla de las cifras globales (la misma con la que se contrastan los
números de referencia): TaxiOut y TaxiIn no nulos y los dos <= 180 min.
Los cancelados no entran, porque no tienen ambos tiempos. Algunos
desviados sí entran si traen ambos tiempos; eso se informa, no se oculta.

La hora del día se saca con división entera de CRSDepTime.
El valor 2400 se pasa a la hora 0. No se usa CAST(CRSDepTime/100 AS INTEGER):
en DuckDB esa división tiene decimales y el CAST redondea, así que
las 23:50–23:59 caían en un grupo falso llamado "24".

Uso (Anaconda Prompt, parado en la carpeta del proyecto):
    conda activate bigdata
    python scripts/calcular_co2.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import config

# Cifras de referencia medidas el 6 de octubre de 2026 sobre este mismo Parquet.
# Si una prueba falla, el cálculo cambió: no se "arregla" el número esperado.
ESPERADO = {
    "filas": 20_928_579,
    "taxiout_nulo": 285_189,
    "taxiin_nulo": 292_087,
    "vuelos_validos": 20_636_222,
    "horas_salida": 6_187_796,
    "horas_llegada": 2_869_540,
    "horas_total": 9_057_336,
    "co2_t_bajo": 10_303_625,
    "co2_t_alto": 20_607_251,
    "grupo_hora_24_cast": 59_378,
    "top_salida_bajo": {
        "ORD": 392_002,
        "DFW": 335_161,
        "DEN": 321_352,
        "ATL": 306_815,
        "CLT": 239_863,
        "LGA": 206_315,
        "SEA": 198_740,
        "LAX": 196_097,
        "LAS": 192_275,
        "JFK": 181_070,
    },
}


def conectar() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    ruta = config.patron_parquet()
    con.execute(
        f"""
        CREATE OR REPLACE VIEW vuelos AS
        SELECT *
        FROM read_parquet('{ruta}', hive_partitioning = true)
        """
    )
    return con


def sql_hora() -> str:
    """Hora programada de salida, de 0 a 23. El 2400 de BTS pasa a las 0."""
    return """
        CASE
            WHEN CRSDepTime = 2400 THEN 0
            WHEN CRSDepTime BETWEEN 0 AND 2359 THEN CRSDepTime // 100
            ELSE NULL
        END
    """


def estadisticas_limpieza(con: duckdb.DuckDBPyConnection | None = None) -> dict:
    """Cuenta filas, nulos, atípicos y el conjunto válido. No borra nada."""
    propio = con is None
    if propio:
        con = conectar()
    tope = config.TAXI_MAX_MIN
    fila = con.execute(
        f"""
        SELECT
            COUNT(*) AS filas,
            SUM(TaxiOut IS NULL)::BIGINT AS taxiout_nulo,
            SUM(TaxiIn IS NULL)::BIGINT AS taxiin_nulo,
            SUM(
                TaxiOut IS NOT NULL AND TaxiIn IS NOT NULL
                AND TaxiOut <= {tope} AND TaxiIn <= {tope}
            )::BIGINT AS vuelos_validos,
            MAX(TaxiOut) AS taxiout_max,
            MAX(TaxiIn) AS taxiin_max,
            ROUND(AVG(TaxiOut), 2) AS taxiout_media,
            MEDIAN(TaxiOut) AS taxiout_mediana,
            ROUND(AVG(TaxiIn), 2) AS taxiin_media,
            MEDIAN(TaxiIn) AS taxiin_mediana,
            SUM(COALESCE(Cancelled, 0) = 1)::BIGINT AS cancelados,
            SUM(COALESCE(Diverted, 0) = 1)::BIGINT AS desviados,
            SUM(CRSDepTime = 2400)::BIGINT AS crs_2400,
            SUM(
                TaxiOut IS NOT NULL AND TaxiIn IS NOT NULL
                AND TaxiOut <= {tope} AND TaxiIn <= {tope}
                AND COALESCE(Diverted, 0) = 1
            )::BIGINT AS desviados_dentro_de_validos,
            SUM(
                TaxiOut IS NOT NULL AND TaxiOut <= {tope}
                AND CRSDepTime < 2400
                AND CAST(CRSDepTime / 100 AS INTEGER) = 24
            )::BIGINT AS grupo_hora_24_cast
        FROM vuelos
        """
    ).fetchdf().iloc[0].to_dict()
    if propio:
        con.close()
    return fila


def _factor_sql(consumo: float) -> str:
    return f"{consumo} * {config.FACTOR_CO2} / 1000.0"


def calcular_agregados(
    consumo_bajo: float | None = None,
    consumo_alto: float | None = None,
    con: duckdb.DuckDBPyConnection | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Agrega el Parquet completo.

    consumo_bajo y consumo_alto están en kg de combustible por minuto.
    Si no se pasan, se usan los dos escenarios de config.py.
    """
    consumo_bajo = config.CONSUMO_KG_MIN_BAJO if consumo_bajo is None else consumo_bajo
    consumo_alto = config.CONSUMO_KG_MIN_ALTO if consumo_alto is None else consumo_alto
    tope = config.TAXI_MAX_MIN
    f_bajo = _factor_sql(consumo_bajo)
    f_alto = _factor_sql(consumo_alto)
    propio = con is None
    if propio:
        con = conectar()

    mes = con.execute(
        f"""
        WITH salida AS (
            SELECT
                Origin AS aeropuerto,
                Year AS anio,
                Month AS mes,
                COUNT(*)::BIGINT AS vuelos_salida,
                SUM(TaxiOut) AS min_rodaje_salida
            FROM vuelos
            WHERE TaxiOut IS NOT NULL AND TaxiOut <= {tope}
            GROUP BY 1, 2, 3
        ),
        llegada AS (
            SELECT
                Dest AS aeropuerto,
                Year AS anio,
                Month AS mes,
                COUNT(*)::BIGINT AS vuelos_llegada,
                SUM(TaxiIn) AS min_rodaje_llegada
            FROM vuelos
            WHERE TaxiIn IS NOT NULL AND TaxiIn <= {tope}
            GROUP BY 1, 2, 3
        )
        SELECT
            COALESCE(s.aeropuerto, l.aeropuerto) AS aeropuerto,
            COALESCE(s.anio, l.anio) AS anio,
            COALESCE(s.mes, l.mes) AS mes,
            COALESCE(s.vuelos_salida, 0) AS vuelos_salida,
            COALESCE(l.vuelos_llegada, 0) AS vuelos_llegada,
            COALESCE(s.vuelos_salida, 0) + COALESCE(l.vuelos_llegada, 0) AS vuelos,
            ROUND(COALESCE(s.min_rodaje_salida, 0), 1) AS min_rodaje_salida,
            ROUND(COALESCE(l.min_rodaje_llegada, 0), 1) AS min_rodaje_llegada,
            ROUND(COALESCE(s.min_rodaje_salida, 0) / 60.0, 2) AS horas_salida,
            ROUND(COALESCE(l.min_rodaje_llegada, 0) / 60.0, 2) AS horas_llegada,
            ROUND(
                (COALESCE(s.min_rodaje_salida, 0) + COALESCE(l.min_rodaje_llegada, 0)) / 60.0,
                2
            ) AS horas,
            ROUND(COALESCE(s.min_rodaje_salida, 0) * {f_bajo}, 3) AS co2_t_bajo_salida,
            ROUND(COALESCE(s.min_rodaje_salida, 0) * {f_alto}, 3) AS co2_t_alto_salida,
            ROUND(COALESCE(l.min_rodaje_llegada, 0) * {f_bajo}, 3) AS co2_t_bajo_llegada,
            ROUND(COALESCE(l.min_rodaje_llegada, 0) * {f_alto}, 3) AS co2_t_alto_llegada,
            ROUND(
                (COALESCE(s.min_rodaje_salida, 0) + COALESCE(l.min_rodaje_llegada, 0)) * {f_bajo},
                3
            ) AS co2_t_bajo,
            ROUND(
                (COALESCE(s.min_rodaje_salida, 0) + COALESCE(l.min_rodaje_llegada, 0)) * {f_alto},
                3
            ) AS co2_t_alto
        FROM salida s
        FULL OUTER JOIN llegada l
            ON s.aeropuerto = l.aeropuerto AND s.anio = l.anio AND s.mes = l.mes
        ORDER BY anio, mes, aeropuerto
        """
    ).fetchdf()

    hora = con.execute(
        f"""
        SELECT
            Origin AS aeropuerto,
            {sql_hora()} AS hora,
            COUNT(*)::BIGINT AS vuelos,
            ROUND(AVG(TaxiOut), 2) AS min_promedio_salida,
            ROUND(SUM(TaxiOut), 1) AS min_rodaje_salida,
            ROUND(SUM(TaxiOut) * {f_bajo}, 3) AS co2_t_bajo,
            ROUND(SUM(TaxiOut) * {f_alto}, 3) AS co2_t_alto
        FROM vuelos
        WHERE TaxiOut IS NOT NULL
          AND TaxiOut <= {tope}
          AND {sql_hora()} IS NOT NULL
        GROUP BY 1, 2
        ORDER BY aeropuerto, hora
        """
    ).fetchdf()

    # Cifras globales: ambos tiempos presentes y <= 180. Así coinciden
    # con las horas y el CO2 de referencia.
    resumen = con.execute(
        f"""
        SELECT
            Year AS anio,
            COUNT(*)::BIGINT AS vuelos,
            ROUND(SUM(TaxiOut) / 60.0, 2) AS horas_salida,
            ROUND(SUM(TaxiIn) / 60.0, 2) AS horas_llegada,
            ROUND((SUM(TaxiOut) + SUM(TaxiIn)) / 60.0, 2) AS horas,
            ROUND((SUM(TaxiOut) + SUM(TaxiIn)) * {f_bajo}, 3) AS co2_t_bajo,
            ROUND((SUM(TaxiOut) + SUM(TaxiIn)) * {f_alto}, 3) AS co2_t_alto
        FROM vuelos
        WHERE TaxiOut IS NOT NULL AND TaxiIn IS NOT NULL
          AND TaxiOut <= {tope} AND TaxiIn <= {tope}
        GROUP BY Year
        ORDER BY Year
        """
    ).fetchdf()

    clima = _rodaje_clima(con, tope)
    clima_indep = _rodaje_clima_independiente(con, tope)
    ahorro = _escenario_ahorro(con, tope, consumo_bajo)

    if propio:
        con.close()

    return {
        "co2_aeropuerto_mes": mes,
        "co2_aeropuerto_hora": hora,
        "resumen_global": resumen,
        "rodaje_clima": clima,
        "rodaje_clima_independiente": clima_indep,
        "escenario_ahorro": ahorro,
    }


def _rodaje_clima(con: duckdb.DuckDBPyConnection, tope: int) -> pd.DataFrame:
    """
    Una sola etiqueta por vuelo, en este orden de prioridad:
    nieve, lluvia fuerte, viento fuerte, lluvia leve, normal.
    Un día con nieve y lluvia queda solo como nieve.
    El notebook compara cada fenómeno por separado.
    """
    if not config.RUTA_CLIMA.exists():
        return pd.DataFrame(columns=["condicion", "vuelos", "min_promedio_salida"])

    ruta_clima = str(config.RUTA_CLIMA).replace("\\", "/")
    lluvia = config.LLUVIA_FUERTE_MM
    viento = config.VIENTO_FUERTE_KMH
    return con.execute(
        f"""
        WITH base AS (
            SELECT
                v.TaxiOut,
                CASE
                    WHEN c.nieve_cm > 0 THEN 'nieve'
                    WHEN c.precipitacion_mm > {lluvia} THEN 'lluvia_fuerte'
                    WHEN c.viento_max_kmh >= {viento} THEN 'viento_fuerte'
                    WHEN c.precipitacion_mm > 0 THEN 'lluvia_leve'
                    ELSE 'normal'
                END AS condicion
            FROM vuelos v
            INNER JOIN read_csv_auto('{ruta_clima}') c
                ON v.Origin = c.Origin
               AND CAST(v.FlightDate AS DATE) = CAST(c.Fecha AS DATE)
            WHERE v.TaxiOut IS NOT NULL AND v.TaxiOut <= {tope}
        )
        SELECT
            condicion,
            COUNT(*)::BIGINT AS vuelos,
            ROUND(AVG(TaxiOut), 2) AS min_promedio_salida
        FROM base
        GROUP BY condicion
        ORDER BY min_promedio_salida DESC
        """
    ).fetchdf()


def _rodaje_clima_independiente(con: duckdb.DuckDBPyConnection, tope: int) -> pd.DataFrame:
    """
    Cada fenómeno se mira solo, sin esconder el viento dentro de la lluvia.
    Un vuelo con lluvia y viento entra en las dos comparaciones.
    """
    if not config.RUTA_CLIMA.exists():
        return pd.DataFrame(columns=["condicion", "vuelos", "min_promedio_salida"])

    ruta_clima = str(config.RUTA_CLIMA).replace("\\", "/")
    lluvia = config.LLUVIA_FUERTE_MM
    viento = config.VIENTO_FUERTE_KMH
    return con.execute(
        f"""
        WITH j AS (
            SELECT
                v.TaxiOut,
                c.precipitacion_mm AS p,
                c.nieve_cm AS nieve,
                c.viento_max_kmh AS viento
            FROM vuelos v
            INNER JOIN read_csv_auto('{ruta_clima}') c
                ON v.Origin = c.Origin
               AND CAST(v.FlightDate AS DATE) = CAST(c.Fecha AS DATE)
            WHERE v.TaxiOut IS NOT NULL AND v.TaxiOut <= {tope}
        )
        SELECT 'lluvia_fuerte' AS condicion, COUNT(*)::BIGINT AS vuelos,
               ROUND(AVG(TaxiOut), 2) AS min_promedio_salida
        FROM j WHERE p > {lluvia}
        UNION ALL
        SELECT 'sin_lluvia', COUNT(*)::BIGINT, ROUND(AVG(TaxiOut), 2)
        FROM j WHERE p = 0 AND nieve = 0
        UNION ALL
        SELECT 'nieve', COUNT(*)::BIGINT, ROUND(AVG(TaxiOut), 2)
        FROM j WHERE nieve > 0
        UNION ALL
        SELECT 'sin_nieve', COUNT(*)::BIGINT, ROUND(AVG(TaxiOut), 2)
        FROM j WHERE nieve = 0
        UNION ALL
        SELECT 'viento_fuerte', COUNT(*)::BIGINT, ROUND(AVG(TaxiOut), 2)
        FROM j WHERE viento >= {viento}
        UNION ALL
        SELECT 'viento_normal', COUNT(*)::BIGINT, ROUND(AVG(TaxiOut), 2)
        FROM j WHERE viento < {viento}
        """
    ).fetchdf()


def _escenario_ahorro(
    con: duckdb.DuckDBPyConnection,
    tope: int,
    consumo_bajo: float,
) -> pd.DataFrame:
    """
    Dos cuentas simples para Sostenibilidad, escenario bajo:
    1) bajar todo el rodaje un 10 % (el CO2 baja el mismo 10 %, porque es lineal);
    2) bajar el rodaje de SALIDA de los aeropuertos lentos hasta la mediana
       de los aeropuertos con más de MIN_VUELOS_RANKING vuelos.
    """
    f_bajo = _factor_sql(consumo_bajo)
    min_vuelos = config.MIN_VUELOS_RANKING
    fila = con.execute(
        f"""
        WITH validos AS (
            SELECT SUM(TaxiOut) + SUM(TaxiIn) AS minutos
            FROM vuelos
            WHERE TaxiOut IS NOT NULL AND TaxiIn IS NOT NULL
              AND TaxiOut <= {tope} AND TaxiIn <= {tope}
        ),
        por_aeropuerto AS (
            SELECT
                Origin AS aeropuerto,
                COUNT(*)::BIGINT AS vuelos,
                AVG(TaxiOut) AS promedio,
                SUM(TaxiOut) AS minutos
            FROM vuelos
            WHERE TaxiOut IS NOT NULL AND TaxiOut <= {tope}
            GROUP BY Origin
        ),
        grandes AS (
            SELECT * FROM por_aeropuerto WHERE vuelos > {min_vuelos}
        ),
        mediana AS (
            SELECT MEDIAN(promedio) AS mediana_min FROM grandes
        ),
        recorte AS (
            SELECT SUM(
                CASE
                    WHEN g.promedio > m.mediana_min
                    THEN (g.promedio - m.mediana_min) * g.vuelos
                    ELSE 0
                END
            ) AS minutos_evitados
            FROM grandes g
            CROSS JOIN mediana m
        )
        SELECT
            (SELECT minutos FROM validos) AS minutos_totales,
            (SELECT minutos FROM validos) * {f_bajo} AS co2_actual,
            (SELECT minutos FROM validos) * 0.10 * {f_bajo} AS evitado_10,
            (SELECT mediana_min FROM mediana) AS mediana_min_salida,
            (SELECT minutos_evitados FROM recorte) AS minutos_hasta_mediana,
            (SELECT minutos_evitados FROM recorte) * {f_bajo} AS evitado_mediana
        """
    ).fetchdf().iloc[0]

    actual = float(fila["co2_actual"])
    evitado_10 = float(fila["evitado_10"])
    evitado_mediana = float(fila["evitado_mediana"])
    return pd.DataFrame(
        [
            {
                "concepto": "bajar_rodaje_10_porciento",
                "detalle": "El CO2 baja el mismo 10 % porque el factor es lineal",
                "co2_t_bajo_actual": round(actual, 3),
                "co2_t_evitado": round(evitado_10, 3),
                "co2_t_bajo_escenario": round(actual - evitado_10, 3),
            },
            {
                "concepto": "salida_lenta_hasta_mediana",
                "detalle": (
                    f"Aeropuertos con más de {min_vuelos} vuelos de salida cuyo "
                    f"promedio supera la mediana ({float(fila['mediana_min_salida']):.2f} min) "
                    "bajan hasta esa mediana. Solo cuenta el rodaje de salida."
                ),
                "co2_t_bajo_actual": round(actual, 3),
                "co2_t_evitado": round(evitado_mediana, 3),
                "co2_t_bajo_escenario": round(actual - evitado_mediana, 3),
            },
        ]
    )


def escribir_resultados(tablas: dict[str, pd.DataFrame]) -> dict[str, Path]:
    """Escribe cada tabla en un archivo temporal y luego lo renombra."""
    config.CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    rutas = {}
    for nombre, df in tablas.items():
        destino = config.CARPETA_RESULTADOS / f"{nombre}.csv"
        temporal = destino.with_suffix(".csv.tmp")
        df.to_csv(temporal, index=False)
        temporal.replace(destino)
        rutas[nombre] = destino
    return rutas


def generar_resultados(
    consumo_bajo: float | None = None,
    consumo_alto: float | None = None,
) -> dict[str, pd.DataFrame]:
    tablas = calcular_agregados(consumo_bajo, consumo_alto)
    escribir_resultados(tablas)
    return tablas


def _cerca(obtenido, esperado, tolerancia=0.6) -> bool:
    return abs(float(obtenido) - float(esperado)) <= tolerancia


def prueba_pandas_un_mes(anio: int = 2023, mes: int = 1) -> None:
    """
    Recalcula un mes con pandas, sin DuckDB, y compara la suma de minutos.
    Sirve para ver que el SQL no se comió ni duplicó filas.
    """
    carpeta = config.CARPETA_PARQUET / f"Year={anio}" / f"Month={mes}"
    archivos = list(carpeta.glob("*.parquet"))
    if not archivos:
        raise AssertionError(f"No hay Parquet en {carpeta}")

    df = pd.read_parquet(archivos)
    tope = config.TAXI_MAX_MIN
    mask = (
        df["TaxiOut"].notna()
        & df["TaxiIn"].notna()
        & (df["TaxiOut"] <= tope)
        & (df["TaxiIn"] <= tope)
    )
    minutos_pandas = float(df.loc[mask, "TaxiOut"].sum() + df.loc[mask, "TaxiIn"].sum())

    con = duckdb.connect()
    ruta = str(carpeta / "*.parquet").replace("\\", "/")
    minutos_duck = float(
        con.execute(
            f"""
            SELECT SUM(TaxiOut) + SUM(TaxiIn)
            FROM read_parquet('{ruta}')
            WHERE TaxiOut IS NOT NULL AND TaxiIn IS NOT NULL
              AND TaxiOut <= {tope} AND TaxiIn <= {tope}
            """
        ).fetchone()[0]
    )
    con.close()
    if not _cerca(minutos_pandas, minutos_duck, tolerancia=0.01):
        raise AssertionError(
            f"Pandas y DuckDB no coinciden en {anio}-{mes}: "
            f"{minutos_pandas} vs {minutos_duck}"
        )


def probar_exactitud(tablas: dict[str, pd.DataFrame] | None = None) -> pd.DataFrame:
    """
    Compara el cálculo con las cifras de referencia.
    Lanza AssertionError si alguna no cuadra.
    """
    calidad = estadisticas_limpieza()
    if tablas is None:
        tablas = calcular_agregados()

    resumen = tablas["resumen_global"]
    horas = float(resumen["horas"].sum())
    co2_bajo = float(resumen["co2_t_bajo"].sum())
    co2_alto = float(resumen["co2_t_alto"].sum())
    vuelos = int(resumen["vuelos"].sum())

    salida = (
        tablas["co2_aeropuerto_mes"]
        .groupby("aeropuerto", as_index=False)["co2_t_bajo_salida"]
        .sum()
    )
    salida["co2_redondeado"] = salida["co2_t_bajo_salida"].round(0).astype(int)
    top = (
        salida.sort_values("co2_redondeado", ascending=False)
        .head(10)
        .set_index("aeropuerto")["co2_redondeado"]
        .to_dict()
    )

    chequeos = [
        ("filas", calidad["filas"], ESPERADO["filas"]),
        ("taxiout_nulo", calidad["taxiout_nulo"], ESPERADO["taxiout_nulo"]),
        ("taxiin_nulo", calidad["taxiin_nulo"], ESPERADO["taxiin_nulo"]),
        ("vuelos_validos", calidad["vuelos_validos"], ESPERADO["vuelos_validos"]),
        ("vuelos_en_resumen", vuelos, ESPERADO["vuelos_validos"]),
        ("horas_salida", float(resumen["horas_salida"].sum()), ESPERADO["horas_salida"]),
        ("horas_llegada", float(resumen["horas_llegada"].sum()), ESPERADO["horas_llegada"]),
        ("horas_total", horas, ESPERADO["horas_total"]),
        ("co2_t_bajo", round(co2_bajo), ESPERADO["co2_t_bajo"]),
        ("co2_t_alto", round(co2_alto), ESPERADO["co2_t_alto"]),
        ("grupo_hora_24_cast", calidad["grupo_hora_24_cast"], ESPERADO["grupo_hora_24_cast"]),
        ("taxiout_media", calidad["taxiout_media"], 17.99),
        ("taxiin_media", calidad["taxiin_media"], 8.35),
    ]

    filas = []
    for nombre, obtenido, esperado in chequeos:
        ok = _cerca(obtenido, esperado)
        filas.append(
            {
                "medida": nombre,
                "esperado": esperado,
                "obtenido": obtenido,
                "cuadra": ok,
            }
        )
        if not ok:
            raise AssertionError(f"{nombre}: esperado {esperado}, obtenido {obtenido}")

    if list(top) != list(ESPERADO["top_salida_bajo"]):
        raise AssertionError(f"El orden del top 10 cambió: {list(top)}")
    for aeropuerto, toneladas in ESPERADO["top_salida_bajo"].items():
        ok = int(top[aeropuerto]) == toneladas
        filas.append(
            {
                "medida": f"top_salida_{aeropuerto}",
                "esperado": toneladas,
                "obtenido": int(top[aeropuerto]),
                "cuadra": ok,
            }
        )
        if not ok:
            raise AssertionError(
                f"{aeropuerto}: esperado {toneladas} t, obtenido {top[aeropuerto]} t"
            )

    prueba_pandas_un_mes()
    return pd.DataFrame(filas)


if __name__ == "__main__":
    print("Calculando CO2 de rodaje sobre el Parquet completo...")
    print(f"Escenario bajo: {config.CONSUMO_KG_MIN_BAJO} kg/min")
    print(f"Escenario alto: {config.CONSUMO_KG_MIN_ALTO} kg/min (POR VALIDAR)")
    print(f"Factor CO2:     {config.FACTOR_CO2} kg CO2 / kg combustible")
    tablas = generar_resultados()
    verificacion = probar_exactitud(tablas)
    salida_verificacion = config.CARPETA_RESULTADOS / "verificacion_exactitud.csv"
    verificacion.to_csv(salida_verificacion, index=False)

    resumen = tablas["resumen_global"]
    print("\nResumen por año (vuelos con ambos tiempos <= 180 min):")
    print(resumen.to_string(index=False))
    print(
        f"\nCO2 total, escenario bajo: {resumen['co2_t_bajo'].sum():,.0f} t"
    )
    print(
        f"CO2 total, escenario alto: {resumen['co2_t_alto'].sum():,.0f} t"
    )
    print("\nCruce con clima (una etiqueta por vuelo):")
    print(tablas["rodaje_clima"].to_string(index=False))
    print("\nEscenarios de ahorro (escenario bajo):")
    print(tablas["escenario_ahorro"].to_string(index=False))
    print(f"\nPruebas de exactitud: {len(verificacion)} chequeos, todos cuadran.")
    print(f"Tablas en {config.CARPETA_RESULTADOS}")
