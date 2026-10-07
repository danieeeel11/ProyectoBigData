# Combustible y CO2 del rodaje en tierra en vuelos de Estados Unidos, 2023-2025

Borrador para pasar a Google Docs. Compartir con rodolfo.meza@gmail.com como editor. Normas APA.

## Resumen ejecutivo

Entre enero de 2023 y diciembre de 2025, los vuelos comerciales de Estados Unidos acumularon **9.057.336 horas** de rodaje en tierra con datos válidos de salida y llegada. Con un consumo de 6 kg de combustible por minuto y el factor 3,16 de la OACI, eso equivale a **10.303.625 toneladas de CO2**. Si el consumo fuera 12 kg/min —cifra todavía por validar— el total se duplica: **20.607.251 toneladas**.

El desperdicio no está repartido parejo. El CO2 de la salida se concentra en ORD, DFW, DEN y ATL. El rodaje más lento, entre aeropuertos con más de 50.000 vuelos, está en JFK (27,0 min), EWR (24,6), LGA (24,2) y ORD (24,2). La hora programada con más CO2 de salida, ya corregida, es las **8** (unas 516 mil toneladas en el escenario bajo), seguida de las 7 y las 6.

De 2023 a 2025 las horas de rodaje subieron **9,0 %**, mientras los vuelos válidos subieron cerca de un 2 %. No es solo que haya más vuelos: cada vuelo pasa más tiempo en tierra.

Bajar todo el rodaje un 10 % evitaría cerca de **1,03 millones de toneladas** en el escenario bajo. El ranking de aeropuertos no cambia si se usa el escenario alto, porque todos se multiplican por el mismo número.

## Pregunta, usuario y decisión

La pregunta es: ¿qué aeropuertos y qué franjas horarias desperdician más combustible rodando en tierra con los motores encendidos, y cuánto CO2 representa eso?

El usuario es el área de Sostenibilidad, que necesita un número para un reporte y una lista corta de dónde actuar. La decisión no es predecir si un vuelo llegará tarde. Ese fue el enfoque anterior del grupo; sus notebooks quedan como apoyo. Aquí el resultado es un inventario de CO2 y un orden de aeropuertos y horas.

La unidad de análisis es el vuelo. `TaxiOut` (minutos desde el puesto hasta el despegue) se atribuye al aeropuerto de origen. `TaxiIn` (desde el aterrizaje hasta el puesto) se atribuye al de destino.

## Metodología

Se sigue CRISP-DM en versión corta:

1. **Negocio.** Reducir combustible de rodaje y reportar CO2. No hace falta un modelo para esa decisión.
2. **Datos.** BTS On-Time Performance, 36 meses, más clima diario de 20 aeropuertos.
3. **Preparación.** Parquet particionado. Regla explícita de limpieza. Hora programada corregida.
4. **Análisis.** Agregados con DuckDB sobre el 100 % de las filas. El mismo cálculo se repite con Dask en dos configuraciones, y un mes se recalcula con pandas.
5. **Evaluación.** 23 comparaciones contra cifras ya medidas. Si una falla, el script se detiene.
6. **Despliegue.** Prefect vuelve a calcular los agregados cuando entra un mes nuevo. A AWS solo suben esas tablas. Grafana las muestra para gerencia.

El modelo de "rodaje excesivo" queda opcional y no bloquea la entrega.

## Datos y volumen

La entrada son 36 ZIP de BTS, **1,05 GB** comprimidos y **9,47 GB** si se descomprimen. El Parquet tiene **20.928.579** filas y ocupa unos **664 MB**. No se perdieron filas en la conversión.

Entran al total los vuelos con `TaxiOut` y `TaxiIn` no nulos y los dos menores o iguales a 180 minutos: **20.636.222**. Se dejan fuera 292.357 filas (1,4 %). Casi todas son nulos. Solo 54 salidas y 219 llegadas superan 180 minutos. Esos extremos se quedan guardados (el máximo es 1.274 min de salida y 1.318 de llegada); no se borran en silencio. Ningún vuelo cancelado queda en el conjunto válido. Sí quedan 48.343 desviados que traen ambos tiempos por debajo del tope; la regla de referencia no los quita.

El detalle de bytes y filas está en `docs/volumenes_por_etapa.md`.

## Exploración

`TaxiOut` promedia **17,99 min** (mediana 15, desviación 9,92). El percentil 90 está en 28 min, el 95 en 35 y el 99 en 56. `TaxiIn` promedia **8,35** (mediana 6). La mayor parte del combustible está en la salida.

`CRSDepTime` es un entero con la hora en formato HHMM, no un texto. Solo 2 vuelos traen 2400. Aun así, dividir por 100 con decimales y convertir a entero redondea: las 23:50–23:59 caen en un grupo falso llamado hora 24 (59.378 salidas válidas). La hora que usa este proyecto es la división entera, y 2400 se guarda como hora 0. Con esa corrección, el promedio más alto y el mayor CO2 están a las **8**, no a las 9.

El día de la semana mueve poco (jueves 18,33 min, sábado 17,59). Enero (18,73) y diciembre (18,52) son los meses más lentos; abril, el más corto (17,55). Southwest aporta más CO2 de salida por cantidad de vuelos, con un promedio corto (13,8 min). United y SkyWest rondan los 20,5 min.

Se marcó como rodaje excesivo de salida el vuelo que supera el percentil 90 de su propio aeropuerto: 1.947.883 vuelos, el 9,44 % de las salidas válidas. Sirve como etiqueta si más adelante hay un modelo. No hace falta para el ranking.

## Prefect

El flujo `ingesta-y-analitica-bts` descarga el mes solo si el ZIP no está, convierte a Parquet solo si ese mes no está marcado como listo, y al final recalcula el CO2 sobre **todo** el Parquet. Una corrida del 6 de octubre de 2026 omitió los 36 meses y dejó 12.164 filas de aeropuerto-mes, 5.169 de aeropuerto-hora y 3 de resumen anual. También actualizó el resumen viejo de atrasos (528 filas), para no perderlo.

Si el ZIP está corrupto o al CSV le faltan `TaxiOut` o `TaxiIn`, el flujo lo escribe en el log y sigue. No borra las particiones buenas ni reemplaza los CSV hasta que el cálculo nuevo termina. Esa prueba se corre con `demostrar_fallo=True`.

## Dask

La misma agregación (CO2 de salida por aeropuerto, hora, año y mes) se corrió el 6 de octubre de 2026 con dos configuraciones. Las dos dieron **7.042.250,7 toneladas** y 128.075 filas, iguales a DuckDB. Esa suma es solo la salida con hora válida; no es el total de 10,3 millones, porque el total también incluye el rodaje de llegada.

| Configuración | Tiempo | Memoria observada |
|---|---:|---:|
| A: 2 workers, 2 hilos, 2 GB cada uno | 5,1 s | 2.018 MB |
| B: 4 workers, 1 hilo, 1 GB cada uno | 9,6 s | 2.441 MB |

Otra vez ganó la configuración con menos procesos. En B un worker llegó al 82 % de su límite de 1 GB y Dask lo pausó. Con este tamaño pesa más coordinar procesos que calcular. La configuración C (4 × 2 GB) no se corrió: había 4,1 GB libres y el script pide al menos 8 GB para no dejar el equipo sin memoria. El archivo del benchmark viejo de atrasos (6,6 s y 12,9 s) se conservó como `benchmark_dask_atrasos.csv`.

## Clima

En los 20 aeropuertos con clima diario, mirando cada fenómeno por separado:

- Nieve: 26,40 min de rodaje de salida, frente a 19,70 sin nieve.
- Lluvia fuerte (más de 5 mm): 22,66 min, frente a 18,88 en un día seco y sin nieve.
- Viento de 40 km/h o más: 22,27 min, frente a 19,96.

No se puede decir que el clima sea la causa única: un día de nieve también desordena la pista. Sí se puede decir que el rodaje se alarga y que un reporte no debería promediar todos los días como si fueran iguales. El dato es diario, no de la hora del vuelo, y no cubre toda la red.

## CO2 y supuestos

`combustible_kg = minutos × kg por minuto`, y `co2_kg = combustible_kg × 3,16`.

| Año | Vuelos válidos | Horas de rodaje | CO2, 6 kg/min (t) | CO2, 12 kg/min (t) |
|---|---:|---:|---:|---:|
| 2023 | 6.758.238 | 2.873.412 | 3.268.794 | 6.537.587 |
| 2024 | 6.981.102 | 3.051.436 | 3.471.314 | 6.942.628 |
| 2025 | 6.896.882 | 3.132.488 | 3.563.518 | 7.127.036 |
| Total | 20.636.222 | 9.057.336 | 10.303.625 | 20.607.251 |

Top 10 de CO2 de **salida**, escenario bajo, en toneladas: ORD 392.002, DFW 335.161, DEN 321.352, ATL 306.815, CLT 239.863, LGA 206.315, SEA 198.740, LAX 196.097, LAS 192.275, JFK 181.070.

Supuestos que hay que dejar escritos: 6 kg/min es una referencia de un A320, no el motor de cada vuelo; 12 kg/min está **por validar**; el empuje en rodaje varía (3 % a 10 %, frente al 7 % de OACI); EUROCONTROL usa 3,15 en lugar de 3,16 y esa diferencia no mueve el ranking.

## AWS y Grafana

A la base solo entran las tablas agregadas. El script `scripts/subir_resultados_aws.py` lee el host y la clave desde `.env`, se puede correr otra vez si el laboratorio se reinicia, y tiene un `--dry-run` que no se conecta. La guía está en `docs/guia_aws_grafana.md`. Los paneles (total, top 10, hora, aeropuertos lentos y ahorro) están descritos en `docs/grafana_paneles.md`, con un JSON para importar.

## Conclusiones

1. En tres años, el rodaje válido representa **10,3 millones de toneladas** de CO2 en el escenario bajo, y el doble si se acepta el escenario alto.
2. Actuar en ORD, DFW, DEN y ATL ataca volumen. Actuar en JFK, EWR, LGA y ORD ataca minutos. ORD está en las dos listas.
3. La mañana (6 a 8) concentra más CO2 de salida que la tarde.
4. Las horas de rodaje crecieron más rápido que el número de vuelos.
5. La nieve y la lluvia fuerte alargan el rodaje de salida en los 20 aeropuertos medidos. No alcanza para atribuirles toda la causa.
6. El grupo "hora 24" era un error de redondeo, no una hora real.

Límites: sin tipo de avión el factor es común a todos los vuelos; el clima no es horario ni nacional; los números son de Estados Unidos.

Trabajo futuro: repetir la metodología con datos de Aerocivil para El Dorado, incorporar el motor cuando exista, y probar si un pronóstico de clima —no el clima ya ocurrido— ayuda a planear la franja de las 6 a las 8.

## Registro de uso de IA

Ver `docs/registro_uso_ia.md`.

## Referencias

Bureau of Transportation Statistics. (s. f.). *Reporting Carrier On-Time Performance*. https://www.transtats.bts.gov

Open-Meteo. (s. f.). *Historical weather API*. https://open-meteo.com

El factor 3,16 kg de CO2 por kg de combustible es el de OACI que fija este proyecto. EUROCONTROL publica 3,15; la diferencia no cambia el ranking. En la versión final del Google Docs hay que pegar el enlace de la página de OACI y el de EUROCONTROL el día en que se consulten. No dejo aquí una ruta de PDF que no se abrió en esta corrida.
