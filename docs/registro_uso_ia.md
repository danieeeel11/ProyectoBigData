# Registro de uso de IA

Curso: Big Data, Maestría en Analítica Aplicada, Universidad de La Sabana.  
Fecha de esta nota: 6 de octubre de 2026.  
Herramienta: Cursor, con un modelo de lenguaje en el editor.

La persona del grupo revisa, corre y explica el resultado. La herramienta no reemplaza esa revisión.

| Qué se pidió | Qué se usó | Cómo se verificó |
|---|---|---|
| Pasar el proyecto de "predecir atrasos" a "CO2 del rodaje en tierra", reutilizando la descarga, el Parquet y el flujo de Prefect. | Se escribió `config.py`, `scripts/calcular_co2.py`, el notebook `notebooks/eda_rodaje_co2.ipynb`, la actualización de Prefect y de Dask, el script de AWS y los textos de `docs/`. | 23 pruebas automáticas comparan el resultado con cifras ya medidas sobre este Parquet (20.928.579 filas, 20.636.222 válidas, 9.057.336 horas, 10.303.625 t y 20.607.251 t, top 10 de salida). Un mes (enero 2023) se recalculó con pandas, sin DuckDB, y la suma de minutos coincidió. |
| Explicar el grupo "hora 24". | La herramienta propuso mirar el tipo de `CRSDepTime` y la división. | `DESCRIBE` muestra que es BIGINT. Hay 2 vuelos con 2400. El CAST redondea 2350–2359 a la hora 24 (59.378 vuelos de salida). La hora corregida usa división entera. |
| No inventar cifras. | Los textos del informe y del notebook citan solo salidas de esas corridas. | Si se vuelve a correr `python scripts/calcular_co2.py` y una prueba falla, el script se detiene. |

Qué no hizo la herramienta: no creó la base en AWS, no armó los paneles dentro de Grafana y no compartió el Google Docs. Eso queda en la guía `docs/guia_aws_grafana.md` para hacerlo en la sesión del laboratorio.

Qué no debe pegarse en el chat ni en Git: host, usuario y contraseña de RDS. Van solo en `.env`.
