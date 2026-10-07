# Checklist — Rodaje en tierra y CO2

Universidad de La Sabana, Maestría en Analítica Aplicada.  
Presentación: **10 de octubre de 2026**. Entrega del documento: **17 de octubre de 2026**.  
Pregunta vigente: ¿qué aeropuertos y qué horas desperdician más combustible en rodaje, y cuánto CO2 es eso?

El enfoque de atrasos (`ArrDel15`) queda como material de apoyo. Este checklist sigue la pregunta nueva.

| Punto | Qué pide el docente | Estado al 6 de octubre | Quién cierra la evidencia |
|---|---|---|---|
| a | Dataset, objetivo y unidad de análisis | Hecho en el README y en el informe. Entrada 9,47 GB, unidad = vuelo | Lina |
| b | EDA, variable objetivo y características | Notebook ejecutado: `notebooks/eda_rodaje_co2.ipynb` | Lina |
| c | Análisis preliminar y contexto | Clima de 20 aeropuertos cruzado con el rodaje. Falta tipo de avión: queda dicho como límite | Lina |
| d | Prefect, recurrente | El flujo corre, omite los 36 meses y recalcula el CO2. Falta la captura del tablero en http://127.0.0.1:4200 | Lina |
| e | Dask, dos configuraciones | Corrido: A 5,1 s y B 9,6 s, misma suma (7.042.250,7 t de salida). Falta la captura del dashboard (`--pausa`) | Lina |
| f | AWS, solo el resultado | Script con `--dry-run` probado. Falta la sesión de RDS y los `SELECT COUNT(*)` | Lina |
| g | Grafana gerencial | Consultas y JSON listos. Falta conectar la base y capturar los paneles | Lina |
| h | Conclusiones | Borrador en `docs/informe_borrador.md`, con los números de la corrida | Compañero 1, revisar |
| i | Documento APA o IEEE | Borrador en Markdown. Falta pasarlo a Google Docs o Word | Compañero 2 |
| j | Compartir con el docente | Pendiente: rodolfo.meza@gmail.com con permiso de **editor** | Lina |
| k | Resultados dentro del documento | Los números ya están en el borrador. Falta pegar gráficas y capturas | Compañero 2 |
| l | GitHub con notebooks y scripts | Código en la rama de trabajo. Falta el commit de esta entrega, sin ZIP ni `.env` | Lina |

## Qué correr y qué capturar

Anaconda Prompt, carpeta del proyecto, `conda activate bigdata`.

1. **Prefect, dos ideas de evidencia.** Terminal 1: `prefect server start`. Terminal 2: `python scripts/flujo_ingesta_prefect.py`. Captura: los meses en "omitido" y el flujo en Completed. Segunda captura: la corrida con fallo controlado (el comando está en el README). Tiene que verse "ZIP corrupto" y "esquema sin TaxiOut/TaxiIn", y el flujo igual termina.
2. **Dask.** `python scripts/benchmark_dask.py --pausa`. Una captura del dashboard por configuración. El CSV debe mostrar la misma suma de CO2 en todas las filas.
3. **RDS.** Estado Available, regla del puerto 5432 solo a tu IP, y los conteos SQL. Guía: `docs/guia_aws_grafana.md`.
4. **Grafana.** Conexión en verde, tablero en escenario bajo, top 10, hora, aeropuertos lentos y ahorro. El JSON está en `docs/grafana_dashboard.json`.
5. **GitHub.** La rama con `config.py`, el notebook, los scripts y `docs/`. Sin `data/raw`, sin `data/parquet`, sin `.env`.

Hay un ZIP que ya estaba dentro de Git antes de ignorar `data/raw`:

`data/raw/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_8.zip` (30,8 MB).

También está seguido `scripts/__pycache__/flujo_ingesta_prefect.cpython-311.pyc`.

Cuando hagas el commit de esta entrega, en Anaconda Prompt o Git Bash, desde la carpeta del proyecto:

```
git rm --cached "data/raw/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_8.zip"
git rm --cached scripts/__pycache__/flujo_ingesta_prefect.cpython-311.pyc
```

Eso los quita del repositorio y los deja en el disco. No borra tus datos.

## Lo que ya cuadró el 6 de octubre

- 20.928.579 filas, 20.636.222 válidas, 9.057.336 horas.
- 10.303.625 t (6 kg/min) y 20.607.251 t (12 kg/min).
- Top 10 de salida idéntico a la medición de referencia, de ORD 392.002 t a JFK 181.070 t.
- Prefect: 36 meses omitidos, fallo controlado detectado, CSV escritos.
- Notebook con salidas visibles y la tabla esperado/obtenido en True.
