# Rodaje en tierra, combustible y CO2 (BTS 2023-2025)

Proyecto de Big Data, Maestría en Analítica Aplicada, Universidad de La Sabana.

**Pregunta:** ¿Qué aeropuertos y qué franjas horarias desperdician más combustible rodando en tierra con los motores encendidos, y cuánto CO2 representa eso?

**Quién lo usa:** Sostenibilidad de una aerolínea o de un aeropuerto.

**Unidad de análisis:** un vuelo. Los resultados se agregan por aeropuerto, hora y mes.

El trabajo anterior (predecir atrasos con `ArrDel15`) sigue en el repositorio como material de apoyo. La pregunta vigente es el CO2 del rodaje.

## Cómo se calcula

Los parámetros están en `config.py`:

| Parámetro | Valor | Nota |
|---|---|---|
| `CONSUMO_KG_MIN_BAJO` | 6 | Unos 0,1 kg/s, referencia de un A320 en rodaje |
| `CONSUMO_KG_MIN_ALTO` | 12 | **Por validar** con la base de motores OACI/EASA |
| `FACTOR_CO2` | 3,16 | kg de CO2 por kg de combustible. EUROCONTROL usa 3,15; aquí no cambia el ranking |
| `TAXI_MAX_MIN` | 180 | Por encima de esto no entra en los totales. El dato sigue en el Parquet |

```
combustible_kg = minutos_rodaje * consumo_kg_por_min
co2_kg         = combustible_kg * 3.16
```

`TaxiOut` se atribuye al aeropuerto de origen. `TaxiIn`, al de destino. El ranking no depende del factor, porque todos los aeropuertos se multiplican por el mismo número. El empuje real en rodaje no es fijo (anda entre 3 % y 10 % según motor y maniobra; OACI supone 7 %). Por eso hay dos escenarios y no una sola cifra.

## Datos

- Fuente: [BTS, Reporting Carrier On-Time Performance](https://transtats.bts.gov/PREZIP/). Archivos mensuales, enero 2023 a diciembre 2025.
- Entrada: 36 ZIP, **1,05 GB** comprimidos y **9,47 GB** descomprimidos.
- Parquet local: **20.928.579** filas, unos 664 MB, en `data/parquet/` (no se sube a GitHub).
- Clima diario de 20 aeropuertos: `data/clima/clima_aeropuertos.csv` (Open-Meteo).

Los ZIP, el Parquet y el archivo `.env` no se suben. Sí se suben los CSV pequeños de `data/resultados/` y de `data/clima/`.

## Orden para correrlo

Abre **Anaconda Prompt**, no PowerShell. `conda` no funciona en la terminal de Cursor.

```
cd C:\Users\linam\Documents\Proyecto\ProyectoBigData
conda activate bigdata
```

1. Medir la entrada (tiene que decir 9,47 GB y que cumple 1,5 GB):

```
python scripts/medir_volumen_entrada.py
```

2. Calcular CO2 y comprobar las cifras de referencia. Si algo no cuadra, el script se detiene:

```
python scripts/calcular_co2.py
```

3. Notebook (en Cursor: Ctrl+Shift+P → Python: Select Interpreter → el ambiente `bigdata`). Ábrelo y recórrelo; ya está ejecutado:

`notebooks/eda_rodaje_co2.ipynb`

4. Prefect. Terminal 1, déjala abierta:

```
prefect server start
```

Terminal 2:

```
python scripts/flujo_ingesta_prefect.py
```

Abre http://127.0.0.1:4200 y toma la captura. Los 36 meses deben decir que se omiten, y al final se recalcula el CO2.

Para la captura del fallo controlado, en la terminal 2 y con Python:

```
python -c "import sys; sys.path.insert(0, 'scripts'); from flujo_ingesta_prefect import flujo_ingesta_bts; import config; flujo_ingesta_bts([(anio, mes) for anio in config.ANIOS for mes in config.MESES], demostrar_fallo=True)"
```

En el log tienen que aparecer "ZIP corrupto" y "esquema sin TaxiOut/TaxiIn", y el flujo debe terminar bien. No borra el Parquet.

5. Dask. Cierra otros programas si la RAM está justa. Para capturar el dashboard, agrega `--pausa`:

```
python scripts/benchmark_dask.py --pausa
```

Sin `--pausa` corre las dos configuraciones y guarda `data/resultados/benchmark_dask.csv`. En la corrida del 6 de octubre, A tardó 5,1 s y B tardó 9,6 s. Las dos sumaron 7.042.250,7 t de CO2 de salida, igual que DuckDB. Ese número no es el total de 10,3 millones: el total también suma la llegada. La configuración C solo entra si hay al menos 8 GB libres. Si el enlace del dashboard no es el puerto 8787, usa el que imprime el script.

6. AWS y Grafana, cuando tengas el laboratorio abierto. Paso a paso: `docs/guia_aws_grafana.md`. Consultas de los paneles: `docs/grafana_paneles.md`.

```
copy .env.example .env
python scripts/subir_resultados_aws.py --dry-run
python scripts/subir_resultados_aws.py
```

## Estructura

```
config.py                          parámetros (consumo, factor, tope, rutas)
notebooks/eda_rodaje_co2.ipynb     EDA del rodaje, ya ejecutado
scripts/calcular_co2.py            agregados y pruebas de exactitud
scripts/flujo_ingesta_prefect.py   descarga, Parquet, CO2, fallo controlado
scripts/benchmark_dask.py          dos configuraciones de workers y memoria
scripts/subir_resultados_aws.py    solo tablas de resultados, credenciales en .env
scripts/medir_volumen_entrada.py   1,05 GB y 9,47 GB
scripts/descargar_clima_openmeteo.py
docs/                              guía AWS, paneles, volúmenes, informe, registro de IA
```

En la raíz siguen los notebooks del enfoque de atrasos. No responden la pregunta nueva.

## Resultado corto

En 20.636.222 vuelos válidos hay **9.057.336 horas** de rodaje. Eso son **10.303.625 toneladas** de CO2 en el escenario bajo y el doble en el alto. La salida pesa más que la llegada. ORD, DFW, DEN y ATL lideran el CO2 de salida. JFK, EWR, LGA y ORD tienen el rodaje de salida más largo. Con la hora corregida, el pico está a las **8**, luego a las 7 y a las 6.

De 2023 a 2025 las horas suben **9 %** y los vuelos solo cerca de un 2 %: cada vuelo pasa más tiempo en tierra.

Bajar el rodaje un 10 % evitaría cerca de **1,03 millones de toneladas** (escenario bajo).

## Límites

- BTS no trae el tipo de avión ni el motor. 6 kg/min es un supuesto, no una medición vuelo a vuelo.
- 12 kg/min está por validar.
- El clima es diario y solo de 20 aeropuertos de origen.
- El dataset es de Estados Unidos. El Dorado queda como trabajo futuro, con la misma metodología y datos de Aerocivil.

## Entrega

El borrador del documento está en `docs/informe_borrador.md`. Hay que pasarlo a Google Docs y compartirlo con **rodolfo.meza@gmail.com** con permiso de **editor**. La lista de capturas está al final de `CHECKLIST_PROYECTO_BIGDATA.md`.
