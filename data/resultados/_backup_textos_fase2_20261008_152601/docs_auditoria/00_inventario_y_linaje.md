# Fase 0 — Inventario y linaje (solo lectura)

Fecha: 8 de octubre de 2026.  
Rama Git: `Lina` (`dfcce22`).  
Entorno: conda `bigdata` (Python 3.11).  
Esta fase **no modificó** `config.py`, scripts productivos, Parquet, CSV de resultados, AWS, Grafana ni el informe final.

## 1. Árbol real del repositorio (ruta confirmada)

Raíz: `C:\Users\linam\Documents\Proyecto\ProyectoBigData`

| Ruta | Rol |
|---|---|
| `config.py` | Parámetros: consumo 6/12, factor 3.16, tope 180, umbrales clima, años 2023–2025 |
| `scripts/calcular_co2.py` | Agregados productivos (DuckDB) y pruebas de regresión históricas |
| `scripts/benchmark_dask.py` | Benchmark Dask vs DuckDB (universo de salida con hora) |
| `scripts/flujo_ingesta_prefect.py` | Descarga ZIP → Parquet + recálculo CO₂ + fallo controlado |
| `scripts/subir_resultados_aws.py` | Carga solo CSV agregados a RDS (`--dry-run` disponible) |
| `scripts/medir_volumen_entrada.py` | Mide ZIP/CSV de entrada |
| `scripts/descargar_clima_openmeteo.py` | Clima diario 20 aeropuertos |
| `scripts/auditar_calidad_rodaje.py` | **Nuevo** (fase 1): auditoría solo lectura |
| `notebooks/eda_rodaje_co2.ipynb` | EDA ejecutado |
| `data/raw/` | 36 ZIP BTS (no Git) |
| `data/parquet/` | 36 particiones `Year=`/`Month=` (no Git) |
| `data/clima/clima_aeropuertos.csv` | Clima diario |
| `data/resultados/*.csv` | Agregados publicados |
| `data/resultados/auditoria/` | **Nuevo**: salidas de la auditoría |
| `data/evidencia/` | Capturas Prefect/Dask |
| `docs/` | Guía AWS/Grafana, paneles, informe borrador, volúmenes |
| `informe_rodaje_co2.docx` | Informe académico (no editado en esta fase) |
| `Rodaje en tierra y CO2 — Presentación.pptx` | Presentación |
| `.env` | Credenciales locales (existe; **no se lee ni se documenta aquí**) |
| `.env.example` | Marcado como borrado en `git status` (`D`) — pendiente de restaurar en fase posterior si se aprueba |

No hay `environment.yml`. `requirements.txt` lista versiones del ambiente.

### Versiones confirmadas en el ambiente

| Paquete | Versión |
|---|---|
| pandas | 3.0.6 |
| pyarrow | 25.0.1 |
| duckdb | 1.5.6 |
| dask / distributed | 2026.8.0 |
| prefect | 3.8.7 |
| sqlalchemy | 2.0.54 |
| psycopg2-binary | 2.9.13 |
| numpy | 2.4.6 |

**No se instaló ni actualizó ningún paquete.**

## 2. Parámetros actuales (`config.py`, confirmado en código)

| Parámetro | Valor | Estado documental |
|---|---|---|
| `CONSUMO_KG_MIN_BAJO` | 6.0 | En uso; justificación pendiente de fuentes primarias (fase 3) |
| `CONSUMO_KG_MIN_ALTO` | 12.0 | Marcado “POR VALIDAR” en código |
| `FACTOR_CO2` | 3.16 | En uso; contraste ICAO pendiente (fase 3) |
| `TAXI_MAX_MIN` | 180 | Excluye del cálculo; no borra el Parquet |
| `MIN_VUELOS_RANKING` | 50000 | Ranking de rodaje lento |
| `LLUVIA_FUERTE_MM` | 5.0 | Umbral sin fuente primaria en repo |
| `VIENTO_FUERTE_KMH` | 40.0 | Umbral sin fuente primaria en repo |
| `ANIOS` / `MESES` | 2023–2025 / 1–12 | Coincide con 36 particiones |

Fórmula en código (`scripts/calcular_co2.py`, `_factor_sql`):

`co2_t = minutos × consumo_kg_min × FACTOR_CO2 / 1000`

## 3. Linaje reconstruido

```
BTS PREZIP ZIP (data/raw/, 36 archivos)
  → CSV interno del ZIP
  → Parquet Hive Year=/Month= (data/parquet/, 20.928.579 filas)
  → scripts/calcular_co2.py / Prefect (DuckDB)
  → CSV en data/resultados/
  → scripts/subir_resultados_aws.py → AWS RDS (tablas agregadas)
  → Grafana (consultas en docs/grafana_paneles.md + JSON)
  → informe_rodaje_co2.docx / presentación
```

Paralelo: Open-Meteo → `data/clima/clima_aeropuertos.csv` → cruce en `calcular_co2.py` y notebook.

## 4. Matriz indicador → universo → fórmula → origen

| Indicador publicado | Universo de filas | Fórmula / regla | Archivo / función | Tabla agregada | Panel / uso |
|---|---|---|---|---|---|
| Filas BTS | Todas las particiones | `COUNT(*)` | Parquet | — | Informe / notebook |
| Vuelos válidos globales 20.636.222 | Ambos `TaxiOut` y `TaxiIn` no nulos y `≤180` | Filtro en SQL | `calcular_co2.calcular_agregados` → `resumen` | `resumen_global.csv` | KPI CO₂ total, informe |
| Horas 9.057.336 | Mismo universo global | `(ΣTaxiOut+ΣTaxiIn)/60` | idem | `resumen_global.csv` | Informe |
| CO₂ 10.303.625 t (6 kg/min) | Mismo universo global | minutos × 6 × 3.16 / 1000 | idem | `resumen_global.csv` | Grafana KPI / informe |
| CO₂ 20.607.251 t (12 kg/min) | Mismo | ×12 | idem | `resumen_global.csv` | Selector escenario alto |
| Top aeropuertos salida | `TaxiOut` no nulo y `≤180` (origen) | Σ minutos salida × factor | CTE `salida` en `calcular_agregados` | `co2_aeropuerto_mes.csv` (`co2_t_bajo_salida`) | Top 10 Grafana |
| CO₂ por hora programada | `TaxiOut` válido + hora de `CRSDepTime` (código actual) | Σ TaxiOut × factor | `co2_aeropuerto_hora` | `co2_aeropuerto_hora.csv` | Panel hora |
| Benchmark Dask 7.042.250,7 t | Salida válida con hora (mismo que panel hora) | Σ TaxiOut × 6 × 3.16 / 1000 | `benchmark_dask.py` | `benchmark_dask.csv` | Evidencia Unidad 3 |
| Ahorro −10 % | Universo **global** (ambos tiempos) | 10 % del CO₂ global | `_escenario_ahorro` | `escenario_ahorro.csv` | Panel ahorro |
| Ahorro hasta mediana | Universo **salida** (>50k vuelos) | minutos por encima de mediana × factor | `_escenario_ahorro` | `escenario_ahorro.csv` | Panel ahorro |
| KPI «operaciones» ≈ 41.279.609 | Obs. salida válida + obs. llegada válida | `COUNT(salida)+COUNT(llegada)` | Confirmado por auditoría (`tramos_salida_mas_llegada=41279609`) | Derivado de `co2_aeropuerto_mes` | Dashboard vivo (no está en el JSON del repo) |
| Clima | Salidas válidas ∩ 20 orígenes con clima | join `Origin`+fecha | `_rodaje_clima*` | `rodaje_clima*.csv` | Opcional / informe |

## 5. Separación de evidencia

| Afirmación | Estado |
|---|---|
| 36 meses 2023–2025, 20.928.579 filas | **Confirmado por ejecución** (auditoría fase 1) |
| Sin duplicados en clave fecha+aerolínea+número+origen+destino+CRSDepTime | **Confirmado por ejecución** |
| Universos distintos global vs salida vs hora | **Confirmado en código** y por ejecución |
| `Dest ≠ Div1Airport` en el 100 % de desviados | **Confirmado por ejecución** |
| Código atribuye `TaxiIn` a `Dest` | **Confirmado en código** (`calcular_co2.py`, CTE `llegada`) |
| HHMM inválidos (minuto >59) no existen; solo 2×2400 | **Confirmado por ejecución** |
| Grupo 24 solo aparece con `CAST(CRSDepTime/100 AS INTEGER)` | **Confirmado por ejecución** (59.378) |
| No hay tipo de avión/motor en el esquema | **Confirmado por ejecución** (solo `Tail_Number` y colas de desviación) |
| Clima cubre ~51 % de salidas válidas | **Confirmado por ejecución** |
| Factor 6/12 y 3.16 son “correctos” científicamente | **Pendiente** (fase 3; no se cambiaron) |
| SQL exacto del KPI “operaciones” en Grafana Cloud | **Pendiente de comprobar** en la instancia viva; el número 41.279.609 cuadra con tramos salida+llegada |
| Zona horaria local vs UTC de `CRSDepTime` | **Inferido / pendiente**: BTS documenta hora local del aeropuerto; no se verificó contra manual BTS en esta fase |

## 6. Respaldo lógico y plan de rollback (antes de cualquier fase posterior)

**No se hizo ningún cambio productivo.** Para cuando se apruebe la fase 2+:

1. Copiar `data/resultados/*.csv` a `data/resultados/_backup_YYYYMMDD/` antes de regenerar.
2. No tocar `data/raw/` ni `data/parquet/`.
3. Generar CSV nuevos en rutas versionadas (p. ej. `data/resultados/v2/`) hasta conciliar.
4. En RDS: cargar a tablas `*_staging` y solo luego reemplazar; conservar el `--dry-run`.
5. Rollback = restaurar CSV del backup y volver a correr `subir_resultados_aws.py`.
6. No usar `git push` ni comandos destructivos sin aprobación.

## 7. Hallazgos de inventario (sin corregir todavía)

### Errores / inconsistencias demostrables en código o datos

1. **Universos mezclados:** `resumen_global` exige ambos tiempos; top/hora/Dask usan solo salida; el ahorro −10 % usa global y el de mediana usa salida. Las cifras no son intercambiables.
2. **Desviados mal atribuidos geográficamente:** los 53.309 desviados tienen `Dest ≠ Div1Airport` en el 100 % de los casos; el código suma `TaxiIn` en `Dest`.
3. **KPI de operaciones 41.279.609** = suma de tramos, no vuelos únicos (20.636.222 / 20.643.336).

### Riesgos por confirmar

- Etiquetas del dashboard vivo (“operaciones”, “13,17 min”) no están en el JSON del repo; hay que auditar SQL real de Grafana (fase 5).
- Justificación científica de 6/12 kg/min y umbrales climáticos (fase 3).

### Decisiones metodológicas abiertas (para fase 2)

Ver cierre de `01_calidad_datos.md`.
