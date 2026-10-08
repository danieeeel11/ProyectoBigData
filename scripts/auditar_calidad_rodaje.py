"""
Auditoría de calidad del Parquet de rodaje (solo lectura).

No modifica config.py, Parquet, ZIP, CSV productivos, AWS ni Grafana.
Escribe solo en data/resultados/auditoria/ y imprime un resumen.

Qué hace, en orden:
  1. Cobertura por año/mes y cruce FlightDate vs particiones.
  2. Búsqueda de duplicados con una clave razonable del esquema.
  3. Desglose de TaxiOut y TaxiIn (nulos, cero, negativos, tope 180).
  4. Validación HHMM de CRSDepTime (hora 0-23 y minuto 0-59).
  5. Desviados: Dest vs Div1Airport y cómo se atribuye TaxiIn hoy.
  6. Clima: cobertura, duplicados Origin/Fecha y riesgo de join 1:N.

Uso (Anaconda Prompt, carpeta del proyecto):
    conda activate bigdata
    cd C:\\Users\\linam\\Documents\\Proyecto\\ProyectoBigData
    python scripts/auditar_calidad_rodaje.py
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd
import psutil

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import config

SALIDA = config.CARPETA_RESULTADOS / "auditoria"
TOPE = config.TAXI_MAX_MIN


def conectar() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    # Solo lectura lógica: no se escribe en Parquet.
    con.execute(
        f"""
        CREATE OR REPLACE VIEW vuelos AS
        SELECT *
        FROM read_parquet('{config.patron_parquet()}', hive_partitioning = true)
        """
    )
    return con


def guardar(df: pd.DataFrame, nombre: str) -> Path:
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / nombre
    df.to_csv(ruta, index=False)
    print(f"  -> {ruta} ({len(df)} filas)")
    return ruta


def cobertura(con: duckdb.DuckDBPyConnection) -> dict:
    print("\n[1] Cobertura e integridad")
    por_mes = con.execute(
        """
        SELECT
            Year AS anio,
            Month AS mes,
            COUNT(*)::BIGINT AS filas,
            COUNT(DISTINCT FlightDate)::BIGINT AS fechas_distintas,
            SUM(
                CAST(Year AS INTEGER) != year(CAST(FlightDate AS DATE))
                OR CAST(Month AS INTEGER) != month(CAST(FlightDate AS DATE))
            )::BIGINT AS fechas_fuera_de_particion
        FROM vuelos
        GROUP BY 1, 2
        ORDER BY 1, 2
        """
    ).fetchdf()
    guardar(por_mes, "cobertura_anio_mes.csv")

    esperado = {(a, m) for a in config.ANIOS for m in config.MESES}
    observado = {(int(r.anio), int(r.mes)) for r in por_mes.itertuples()}
    faltan = sorted(esperado - observado)
    sobran = sorted(observado - esperado)

    resumen = {
        "filas_total": int(por_mes["filas"].sum()),
        "meses_observados": len(observado),
        "meses_esperados": len(esperado),
        "meses_faltantes": faltan,
        "meses_fuera_rango": sobran,
        "fechas_fuera_de_particion": int(por_mes["fechas_fuera_de_particion"].sum()),
    }
    print(
        f"  Filas={resumen['filas_total']:,} | meses={resumen['meses_observados']}/36 | "
        f"fechas fuera de partición={resumen['fechas_fuera_de_particion']:,}"
    )
    if faltan:
        print(f"  FALTAN meses: {faltan}")
    if sobran:
        print(f"  Sobran meses fuera de 2023-2025: {sobran}")
    return resumen


def esquema_y_nulos(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    print("\n[2] Esquema y nulos de campos críticos")
    esquema = con.execute("DESCRIBE SELECT * FROM vuelos").fetchdf()
    guardar(esquema, "esquema_parquet.csv")

    criticos = [
        "FlightDate", "Year", "Month", "DayOfWeek", "Reporting_Airline",
        "Flight_Number_Reporting_Airline", "Tail_Number", "Origin", "Dest",
        "CRSDepTime", "TaxiOut", "TaxiIn", "Cancelled", "Diverted",
        "Div1Airport", "DivActualElapsedTime", "Distance",
    ]
    presentes = set(esquema["column_name"])
    filas = []
    for col in criticos:
        if col not in presentes:
            filas.append({"columna": col, "presente": False, "nulos": None, "no_nulos": None})
            continue
        nulos, no_nulos = con.execute(
            f"SELECT SUM({col} IS NULL)::BIGINT, SUM({col} IS NOT NULL)::BIGINT FROM vuelos"
        ).fetchone()
        filas.append(
            {
                "columna": col,
                "presente": True,
                "nulos": int(nulos),
                "no_nulos": int(no_nulos),
            }
        )
    df = pd.DataFrame(filas)
    guardar(df, "nulos_campos_criticos.csv")

    # ¿Hay tipo de avión / motor / matrícula explotable?
    candidatos = [
        c for c in presentes
        if any(x in c.lower() for x in ("aircraft", "equip", "tail", "engine", "motor", "type"))
    ]
    print(f"  Columnas tipo/avion/motor/tail encontradas: {sorted(candidatos)}")
    return df


def duplicados(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    print("\n[3] Duplicados (clave operativa candidata)")
    # Clave alineada con la identidad reportada por BTS: fecha + aerolínea + número + origen.
    # Tail_Number se deja fuera porque puede ser nulo.
    clave = """
        FlightDate,
        Reporting_Airline,
        Flight_Number_Reporting_Airline,
        Origin,
        Dest,
        CRSDepTime
    """
    resumen = con.execute(
        f"""
        WITH g AS (
            SELECT {clave}, COUNT(*)::BIGINT AS n
            FROM vuelos
            GROUP BY {clave}
        )
        SELECT
            COUNT(*)::BIGINT AS grupos,
            SUM(n)::BIGINT AS filas_cubiertas,
            SUM(CASE WHEN n > 1 THEN 1 ELSE 0 END)::BIGINT AS grupos_duplicados,
            SUM(CASE WHEN n > 1 THEN n ELSE 0 END)::BIGINT AS filas_en_grupos_duplicados,
            MAX(n) AS max_repeticiones
        FROM g
        """
    ).fetchdf()
    guardar(resumen, "duplicados_resumen.csv")

    ejemplos = con.execute(
        f"""
        SELECT {clave}, COUNT(*)::BIGINT AS n
        FROM vuelos
        GROUP BY {clave}
        HAVING COUNT(*) > 1
        ORDER BY n DESC
        LIMIT 20
        """
    ).fetchdf()
    guardar(ejemplos, "duplicados_ejemplos.csv")
    print(resumen.to_string(index=False))
    return resumen


def calidad_tiempos(con: duckdb.DuckDBPyConnection) -> None:
    print("\n[4] Calidad TaxiOut / TaxiIn")
    for var in ("TaxiOut", "TaxiIn"):
        df = con.execute(
            f"""
            SELECT
                Year AS anio,
                COUNT(*)::BIGINT AS filas,
                SUM({var} IS NULL)::BIGINT AS nulos,
                SUM({var} IS NOT NULL AND {var} < 0)::BIGINT AS negativos,
                SUM({var} = 0)::BIGINT AS cero,
                SUM({var} > 0 AND {var} < {TOPE})::BIGINT AS entre_0_y_tope,
                SUM({var} = {TOPE})::BIGINT AS igual_tope,
                SUM({var} > {TOPE})::BIGINT AS sobre_tope,
                ROUND(MIN({var}), 2) AS minimo,
                ROUND(MAX({var}), 2) AS maximo,
                ROUND(AVG({var}), 4) AS media,
                MEDIAN({var}) AS mediana,
                QUANTILE_CONT({var}, 0.90) AS p90,
                QUANTILE_CONT({var}, 0.99) AS p99,
                ROUND(SUM(CASE WHEN {var} > {TOPE} THEN {var} ELSE 0 END), 1) AS minutos_sobre_tope,
                ROUND(SUM(CASE WHEN {var} > {TOPE} THEN {var} ELSE 0 END)
                      * {config.CONSUMO_KG_MIN_BAJO} * {config.FACTOR_CO2} / 1000, 1)
                    AS co2_t_bajo_si_se_incluyeran_sobre_tope
            FROM vuelos
            GROUP BY Year
            ORDER BY Year
            """
        ).fetchdf()
        guardar(df, f"calidad_{var.lower()}_por_anio.csv")
        print(f"  {var}:")
        print(df[["anio", "nulos", "negativos", "cero", "igual_tope", "sobre_tope", "maximo"]].to_string(index=False))

    cruces = con.execute(
        f"""
        SELECT
            Year AS anio,
            SUM(TaxiOut IS NOT NULL AND TaxiOut <= {TOPE}
                AND TaxiIn IS NOT NULL AND TaxiIn <= {TOPE})::BIGINT AS ambos_validos,
            SUM(TaxiOut IS NOT NULL AND TaxiOut <= {TOPE}
                AND (TaxiIn IS NULL OR TaxiIn > {TOPE}))::BIGINT AS solo_salida_valida,
            SUM(TaxiIn IS NOT NULL AND TaxiIn <= {TOPE}
                AND (TaxiOut IS NULL OR TaxiOut > {TOPE}))::BIGINT AS solo_llegada_valida,
            SUM((TaxiOut IS NULL OR TaxiOut > {TOPE})
                AND (TaxiIn IS NULL OR TaxiIn > {TOPE}))::BIGINT AS ninguno_valido,
            SUM(COALESCE(Cancelled, 0) = 1)::BIGINT AS cancelados,
            SUM(COALESCE(Diverted, 0) = 1)::BIGINT AS desviados,
            SUM(TaxiOut IS NOT NULL AND TaxiOut <= {TOPE}
                AND TaxiIn IS NOT NULL AND TaxiIn <= {TOPE}
                AND COALESCE(Cancelled, 0) = 1)::BIGINT AS cancelados_en_ambos,
            SUM(TaxiOut IS NOT NULL AND TaxiOut <= {TOPE}
                AND TaxiIn IS NOT NULL AND TaxiIn <= {TOPE}
                AND COALESCE(Diverted, 0) = 1)::BIGINT AS desviados_en_ambos,
            -- sensibilidad: totales de minutos con y sin tope (solo no nulos)
            ROUND(SUM(CASE WHEN TaxiOut IS NOT NULL THEN TaxiOut ELSE 0 END)
                + SUM(CASE WHEN TaxiIn IS NOT NULL THEN TaxiIn ELSE 0 END), 1) AS min_sin_tope_ambos_disponibles_por_separado,
            ROUND(SUM(CASE WHEN TaxiOut IS NOT NULL AND TaxiOut <= {TOPE} THEN TaxiOut ELSE 0 END)
                + SUM(CASE WHEN TaxiIn IS NOT NULL AND TaxiIn <= {TOPE} THEN TaxiIn ELSE 0 END), 1) AS min_con_tope_por_separado
        FROM vuelos
        GROUP BY Year
        ORDER BY Year
        """
    ).fetchdf()
    guardar(cruces, "universos_por_anio.csv")
    print("  Universos por año:")
    print(cruces[["anio", "ambos_validos", "solo_salida_valida", "solo_llegada_valida", "ninguno_valido", "desviados_en_ambos"]].to_string(index=False))


def hhmm(con: duckdb.DuckDBPyConnection) -> None:
    print("\n[5] CRSDepTime (HHMM)")
    # Un HHMM válido: 0..2359, con minuto 0..59. 2400 se trata aparte (convención medianoche).
    df = con.execute(
        """
        WITH base AS (
            SELECT
                CRSDepTime,
                CASE
                    WHEN CRSDepTime IS NULL THEN 'nulo'
                    WHEN CRSDepTime = 2400 THEN '2400_medianoche'
                    WHEN CRSDepTime < 0 THEN 'negativo'
                    WHEN CRSDepTime > 2400 THEN 'mayor_2400'
                    WHEN CRSDepTime > 2359 AND CRSDepTime < 2400 THEN '2360_a_2399'
                    WHEN (CRSDepTime % 100) > 59 THEN 'minuto_invalido_0_2359'
                    WHEN (CRSDepTime // 100) > 23 THEN 'hora_invalida'
                    ELSE 'hhmm_valido'
                END AS clase,
                CASE
                    WHEN CRSDepTime = 2400 THEN 0
                    WHEN CRSDepTime BETWEEN 0 AND 2359 THEN CRSDepTime // 100
                    ELSE NULL
                END AS hora_codigo_actual,
                CASE
                    WHEN CRSDepTime = 2400 THEN 0
                    WHEN CRSDepTime BETWEEN 0 AND 2359 AND (CRSDepTime % 100) <= 59
                        THEN CRSDepTime // 100
                    ELSE NULL
                END AS hora_hhmm_estricto
            FROM vuelos
        )
        SELECT clase, COUNT(*)::BIGINT AS vuelos
        FROM base
        GROUP BY 1
        ORDER BY vuelos DESC
        """
    ).fetchdf()
    guardar(df, "crsdeptime_clases.csv")
    print(df.to_string(index=False))

    grupos = con.execute(
        f"""
        SELECT
            SUM(CASE
                    WHEN CRSDepTime = 2400 THEN 0
                    WHEN CRSDepTime BETWEEN 0 AND 2359 THEN CRSDepTime // 100
                END = 24)::BIGINT AS grupo24_codigo_actual,
            SUM(CASE
                    WHEN CRSDepTime = 2400 THEN 0
                    WHEN CRSDepTime BETWEEN 0 AND 2359 AND (CRSDepTime % 100) <= 59
                        THEN CRSDepTime // 100
                END = 24)::BIGINT AS grupo24_hhmm_estricto,
            SUM(CAST(CRSDepTime / 100 AS INTEGER) = 24 AND CRSDepTime < 2400)::BIGINT AS grupo24_cast,
            SUM(CRSDepTime BETWEEN 0 AND 2359 AND (CRSDepTime % 100) > 59)::BIGINT AS minuto_invalido_total,
            SUM(CRSDepTime = 2400)::BIGINT AS valor_2400,
            SUM(CRSDepTime < 0)::BIGINT AS negativos,
            SUM(CRSDepTime > 2400)::BIGINT AS mayores_2400
        FROM vuelos
        WHERE TaxiOut IS NOT NULL AND TaxiOut <= {TOPE}
        """
    ).fetchdf()
    guardar(grupos, "crsdeptime_grupos24.csv")
    print(grupos.to_string(index=False))

    ejemplos_invalidos = con.execute(
        """
        SELECT CRSDepTime, COUNT(*)::BIGINT AS n
        FROM vuelos
        WHERE CRSDepTime IS NOT NULL
          AND (
                CRSDepTime < 0
             OR CRSDepTime > 2400
             OR (CRSDepTime BETWEEN 0 AND 2359 AND (CRSDepTime % 100) > 59)
             OR (CRSDepTime > 2359 AND CRSDepTime < 2400)
          )
        GROUP BY 1
        ORDER BY n DESC
        LIMIT 30
        """
    ).fetchdf()
    guardar(ejemplos_invalidos, "crsdeptime_invalidos_ejemplos.csv")
    if len(ejemplos_invalidos):
        print("  Ejemplos de HHMM inválidos:")
        print(ejemplos_invalidos.to_string(index=False))
    else:
        print("  No aparecieron HHMM inválidos fuera de la clase 2400.")


def desviados(con: duckdb.DuckDBPyConnection) -> None:
    print("\n[6] Desviados y aeropuerto de llegada")
    resumen = con.execute(
        f"""
        SELECT
            SUM(COALESCE(Diverted, 0) = 1)::BIGINT AS desviados,
            SUM(COALESCE(Diverted, 0) = 1 AND Div1Airport IS NOT NULL)::BIGINT AS con_div1,
            SUM(COALESCE(Diverted, 0) = 1 AND Div1Airport IS NULL)::BIGINT AS sin_div1,
            SUM(COALESCE(Diverted, 0) = 1 AND Dest IS NOT NULL)::BIGINT AS con_dest,
            SUM(COALESCE(Diverted, 0) = 1 AND Dest <> Div1Airport
                AND Div1Airport IS NOT NULL)::BIGINT AS dest_distinto_div1,
            SUM(COALESCE(Diverted, 0) = 1 AND Dest = Div1Airport
                AND Div1Airport IS NOT NULL)::BIGINT AS dest_igual_div1,
            SUM(COALESCE(Diverted, 0) = 1 AND TaxiIn IS NOT NULL AND TaxiIn <= {TOPE})::BIGINT AS desviados_taxiin_valido,
            SUM(COALESCE(Diverted, 0) = 1 AND TaxiOut IS NOT NULL AND TaxiOut <= {TOPE}
                AND TaxiIn IS NOT NULL AND TaxiIn <= {TOPE})::BIGINT AS desviados_ambos_validos,
            ROUND(SUM(CASE
                WHEN COALESCE(Diverted, 0) = 1 AND TaxiIn IS NOT NULL AND TaxiIn <= {TOPE}
                THEN TaxiIn ELSE 0 END), 1) AS minutos_taxiin_desviado_valido,
            ROUND(SUM(CASE
                WHEN COALESCE(Diverted, 0) = 1 AND TaxiIn IS NOT NULL AND TaxiIn <= {TOPE}
                THEN TaxiIn * {config.CONSUMO_KG_MIN_BAJO} * {config.FACTOR_CO2} / 1000
                ELSE 0 END), 3) AS co2_t_bajo_taxiin_desviado
        FROM vuelos
        """
    ).fetchdf()
    guardar(resumen, "desviados_resumen.csv")
    print(resumen.T.to_string(header=False))

    # Impacto de la regla actual: TaxiIn se atribuye a Dest aunque haya Div1Airport distinto.
    impacto = con.execute(
        f"""
        SELECT
            Dest AS aeropuerto_dest,
            Div1Airport AS aeropuerto_div1,
            COUNT(*)::BIGINT AS vuelos,
            ROUND(SUM(TaxiIn), 1) AS min_taxiin,
            ROUND(SUM(TaxiIn) * {config.CONSUMO_KG_MIN_BAJO} * {config.FACTOR_CO2} / 1000, 3) AS co2_t_bajo
        FROM vuelos
        WHERE COALESCE(Diverted, 0) = 1
          AND TaxiIn IS NOT NULL AND TaxiIn <= {TOPE}
          AND Div1Airport IS NOT NULL
          AND Dest <> Div1Airport
        GROUP BY 1, 2
        ORDER BY co2_t_bajo DESC
        LIMIT 20
        """
    ).fetchdf()
    guardar(impacto, "desviados_dest_vs_div1_top.csv")
    print(f"  Pares Dest distinto de Div1Airport con TaxiIn valido: {len(impacto)} (top guardado)")


def clima(con: duckdb.DuckDBPyConnection) -> None:
    print("\n[7] Clima")
    if not config.RUTA_CLIMA.exists():
        print("  No existe el CSV de clima.")
        return
    ruta = str(config.RUTA_CLIMA).replace("\\", "/")
    calidad = con.execute(
        f"""
        WITH c AS (
            SELECT * FROM read_csv_auto('{ruta}')
        ),
        dup AS (
            SELECT Origin, Fecha, COUNT(*)::BIGINT AS n
            FROM c
            GROUP BY 1, 2
            HAVING COUNT(*) > 1
        )
        SELECT
            (SELECT COUNT(*) FROM c)::BIGINT AS filas_clima,
            (SELECT COUNT(DISTINCT Origin) FROM c)::BIGINT AS aeropuertos,
            (SELECT COUNT(*) FROM dup)::BIGINT AS pares_origin_fecha_duplicados,
            (SELECT COALESCE(SUM(n), 0) FROM dup)::BIGINT AS filas_en_duplicados
        """
    ).fetchdf()
    guardar(calidad, "clima_calidad.csv")
    print(calidad.to_string(index=False))

    cobertura = con.execute(
        f"""
        WITH c AS (
            SELECT Origin, CAST(Fecha AS DATE) AS fecha
            FROM read_csv_auto('{ruta}')
        ),
        v AS (
            SELECT Origin, CAST(FlightDate AS DATE) AS fecha, TaxiOut
            FROM vuelos
            WHERE TaxiOut IS NOT NULL AND TaxiOut <= {TOPE}
        )
        SELECT
            COUNT(*)::BIGINT AS salidas_validas,
            SUM(c.Origin IS NOT NULL)::BIGINT AS con_clima,
            SUM(c.Origin IS NULL)::BIGINT AS sin_clima,
            ROUND(100.0 * SUM(c.Origin IS NOT NULL) / COUNT(*), 2) AS pct_con_clima
        FROM v
        LEFT JOIN c ON v.Origin = c.Origin AND v.fecha = c.fecha
        """
    ).fetchdf()
    guardar(cobertura, "clima_cobertura_salidas.csv")
    print(cobertura.to_string(index=False))

    # Detectar multiplicación por join 1:N
    multi = con.execute(
        f"""
        WITH c AS (
            SELECT Origin, CAST(Fecha AS DATE) AS fecha, COUNT(*)::BIGINT AS n
            FROM read_csv_auto('{ruta}')
            GROUP BY 1, 2
        )
        SELECT
            SUM(n > 1)::BIGINT AS dias_con_mas_de_una_fila,
            MAX(n) AS max_filas_por_dia
        FROM c
        """
    ).fetchdf()
    guardar(multi, "clima_multiplicacion_join.csv")
    print(multi.to_string(index=False))


def conciliacion_borrador(con: duckdb.DuckDBPyConnection) -> None:
    print("\n[8] Borrador de conciliación entre universos publicados")
    # Universos que ya usa el código productivo (sin modificarlo).
    df = con.execute(
        f"""
        WITH
        global AS (
            SELECT
                SUM(TaxiOut)::DOUBLE AS min_out,
                SUM(TaxiIn)::DOUBLE AS min_in,
                COUNT(*)::BIGINT AS vuelos
            FROM vuelos
            WHERE TaxiOut IS NOT NULL AND TaxiIn IS NOT NULL
              AND TaxiOut <= {TOPE} AND TaxiIn <= {TOPE}
        ),
        salida AS (
            SELECT SUM(TaxiOut)::DOUBLE AS min_out, COUNT(*)::BIGINT AS obs
            FROM vuelos
            WHERE TaxiOut IS NOT NULL AND TaxiOut <= {TOPE}
        ),
        llegada AS (
            SELECT SUM(TaxiIn)::DOUBLE AS min_in, COUNT(*)::BIGINT AS obs
            FROM vuelos
            WHERE TaxiIn IS NOT NULL AND TaxiIn <= {TOPE}
        ),
        salida_hora AS (
            SELECT SUM(TaxiOut)::DOUBLE AS min_out, COUNT(*)::BIGINT AS obs
            FROM vuelos
            WHERE TaxiOut IS NOT NULL AND TaxiOut <= {TOPE}
              AND (
                    CRSDepTime = 2400
                 OR CRSDepTime BETWEEN 0 AND 2359
              )
        )
        SELECT
            g.vuelos AS vuelos_ambos_validos,
            ROUND((g.min_out + g.min_in) / 60.0, 2) AS horas_global,
            ROUND((g.min_out + g.min_in) * {config.CONSUMO_KG_MIN_BAJO} * {config.FACTOR_CO2} / 1000, 3) AS co2_t_bajo_global,
            s.obs AS obs_salida_valida,
            ROUND(s.min_out * {config.CONSUMO_KG_MIN_BAJO} * {config.FACTOR_CO2} / 1000, 3) AS co2_t_bajo_solo_salida,
            l.obs AS obs_llegada_valida,
            ROUND(l.min_in * {config.CONSUMO_KG_MIN_BAJO} * {config.FACTOR_CO2} / 1000, 3) AS co2_t_bajo_solo_llegada,
            (s.obs + l.obs) AS tramos_salida_mas_llegada,
            sh.obs AS obs_salida_con_hora_codigo_actual,
            ROUND(sh.min_out * {config.CONSUMO_KG_MIN_BAJO} * {config.FACTOR_CO2} / 1000, 3) AS co2_t_bajo_salida_hora
        FROM global g, salida s, llegada l, salida_hora sh
        """
    ).fetchdf()
    guardar(df, "conciliacion_universos.csv")
    print(df.T.to_string(header=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditoría de solo lectura del Parquet de rodaje")
    parser.parse_args()

    inicio = time.perf_counter()
    proceso = psutil.Process()
    mem0 = proceso.memory_info().rss / 1e6
    print("Auditoría de calidad — solo lectura")
    print(f"Parquet: {config.CARPETA_PARQUET}")
    print(f"Salida:  {SALIDA}")
    print(f"Tope usado solo para medir (no se cambia): {TOPE} min")
    print(f"RAM del proceso al inicio: {mem0:.0f} MB")

    con = conectar()
    cov = cobertura(con)
    esquema_y_nulos(con)
    duplicados(con)
    calidad_tiempos(con)
    hhmm(con)
    desviados(con)
    clima(con)
    conciliacion_borrador(con)
    con.close()

    segundos = time.perf_counter() - inicio
    mem1 = proceso.memory_info().rss / 1e6
    meta = pd.DataFrame(
        [
            {
                "segundos": round(segundos, 2),
                "ram_inicio_mb": round(mem0, 1),
                "ram_final_mb": round(mem1, 1),
                "filas_total": cov["filas_total"],
                "meses_ok": cov["meses_observados"] == 36 and not cov["meses_faltantes"],
            }
        ]
    )
    guardar(meta, "meta_ejecucion.csv")
    print(f"\nListo en {segundos:.1f} s | RAM final ~{mem1:.0f} MB")
    print("No se modificó ningún dato productivo.")


if __name__ == "__main__":
    main()
