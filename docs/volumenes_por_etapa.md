# Volúmenes por etapa

Medido el 6 de octubre de 2026 en este equipo, sobre los 36 meses de BTS (enero 2023 a diciembre 2025). Ninguna etapa analítica usa una muestra.

| Etapa | Qué es | Bytes | Registros | Qué se hizo y por qué |
|---|---|---:|---:|---|
| ZIP | Entrada descargada de BTS | 1.049.533.684 (1,05 GB) | 36 archivos | Se conserva comprimida. No se sube a Git ni a AWS. |
| CSV dentro de los ZIP | Entrada descomprimida, sin duplicar a disco | 9,47 GB | 36 CSV, uno por mes | Es el volumen que exige el docente (más de 1,5 GB). `scripts/medir_volumen_entrada.py` lo lee del índice del ZIP. |
| Parquet | Misma información, columnar, partido por año y mes | 696.312.668 (664 MB) | 20.928.579 filas | Compresión columnar. No se pierden filas frente al CSV. |
| Vuelos válidos para el total | Ambos tiempos de rodaje presentes y ≤ 180 min | — | 20.636.222 | Se excluyen 292.357 filas (1,4 %), casi todas por dato nulo. Solo 54 salidas y 219 llegadas superan 180 min; el máximo (1.274 y 1.318 min) se documenta y sigue en el Parquet. |
| `resumen_global.csv` | CO2 por año | pequeño | 3 | Un año por fila. |
| `co2_aeropuerto_mes.csv` | Aeropuerto × año × mes, salida y llegada separadas | pequeño | 12.164 | Cada vuelo suma TaxiOut en el origen y TaxiIn en el destino. |
| `co2_aeropuerto_hora.csv` | Aeropuerto × hora de salida (0–23) | pequeño | 5.169 | Hora con división entera. 2400 pasa a la hora 0. |
| `rodaje_clima.csv` | Clima con una etiqueta por vuelo | pequeño | 5 | Solo 20 aeropuertos de origen. |
| `rodaje_clima_independiente.csv` | Lluvia, nieve y viento por separado | pequeño | 6 | Evita que el viento quede escondido dentro de la lluvia. |
| `escenario_ahorro.csv` | 10 % y mediana | pequeño | 2 | Escenario bajo. |
| AWS RDS | Solo las tablas de arriba | — | las mismas filas | Nunca el ZIP ni el Parquet. |

Tiempos observados en esta máquina (12 núcleos, 16 GB de RAM):

- Recalcular todos los agregados de CO2 con DuckDB: alrededor de 15 segundos.
- Flujo de Prefect sobre los 36 meses ya convertidos: los omite y vuelve a calcular el CO2 en menos de 20 segundos.
- Dask, misma suma de CO2 de salida (7.042.250,7 t, 128.075 filas, igual a DuckDB): configuración A (2 workers, 2 hilos, 2 GB) en 5,1 s; configuración B (4 workers, 1 hilo, 1 GB) en 9,6 s. La C no corrió porque solo había 4,1 GB libres. El benchmark viejo de atrasos (6,6 s y 12,9 s) quedó en `benchmark_dask_atrasos.csv`.

La reducción de 9,47 GB a unos miles de filas es una agregación justificada: la pregunta se responde por aeropuerto, hora y mes, no vuelo por vuelo. El conteo de 20.928.579 filas demuestra que el cálculo partió del conjunto completo.
