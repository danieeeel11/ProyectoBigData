# Fase 1 — Auditoría de calidad del Parquet (solo lectura)

Fecha de ejecución: 8 de octubre de 2026.  
Script: `scripts/auditar_calidad_rodaje.py`  
Salidas: `data/resultados/auditoria/` (CSV nuevos; **no se sobrescribieron** resultados productivos).  
Duración: **18,7 s**. RAM del proceso: ~96 MB → ~133 MB.  
Parámetros 6 / 12 / 3.16 / 180: **solo se usaron para medir impacto; no se modificaron.**

Comando (Anaconda Prompt):

```
cd C:\Users\linam\Documents\Proyecto\ProyectoBigData
conda activate bigdata
python scripts/auditar_calidad_rodaje.py
```

---

## 1. Cobertura e integridad

| Medida | Resultado |
|---|---:|
| Filas totales | **20.928.579** |
| Meses observados 2023–2025 | **36 / 36** |
| Particiones faltantes o fuera de rango | 0 |
| `FlightDate` fuera de `Year`/`Month` de partición | **0** |
| Duplicados (clave: `FlightDate + Reporting_Airline + Flight_Number_Reporting_Airline + Origin + Dest + CRSDepTime`) | **0** |

Archivos: `cobertura_anio_mes.csv`, `duplicados_resumen.csv`.

**Conclusión:** el Parquet está completo y sin colisiones en esa clave. No hay evidencia de filas duplicadas auténticas con esa definición.

### Esquema explotable

- 110 columnas en el Parquet (`esquema_parquet.csv`).
- Presentes: `Tail_Number` (48.139 nulos), `Div1Airport`, `DivActualElapsedTime`, `Diverted`, `Cancelled`.
- **No hay** columna de tipo de avión, motor ni equipo. Solo matrícula (`Tail_Number`) y colas de desviación (`Div1TailNum`…).
- Por tanto, **no es posible hoy** un modelo de consumo por aeronave verificable con este dataset solo.

---

## 2. Calidad de `TaxiOut` / `TaxiIn`

### Desglose (totales 2023–2025)

| Variable | Nulos | Negativos | Cero | `=180` | `>180` | Máximo |
|---|---:|---:|---:|---:|---:|---:|
| TaxiOut | 285.189 | 0 | 0 | 7 | 54 | 1.274 |
| TaxiIn | 292.087 | 0 | 0 | 5 | 219 | 1.318 |

No hay valores cero ni negativos. Adoptar una regla `> 0` **no cambia** el universo actual (todos los no nulos son ≥ 1).

### Impacto del tope 180 (sensibilidad, sin cambiar la regla)

| Variable | Filas `>180` | Minutos excluidos | CO₂ escenario bajo si se incluyeran |
|---|---:|---:|---:|
| TaxiOut | 54 | 14.600 | **276,8 t** |
| TaxiIn | 219 | 48.990 | **928,9 t** |

El tope mueve ~1.206 t en total (~0,01 % del CO₂ global de 10,3 Mt). Es un filtro de cola extrema, no el motor del resultado. Los extremos siguen en el Parquet.

### Universos por año (regla actual `≤180`)

| Año | Ambos válidos | Solo salida | Solo llegada | Ninguno | Desviados dentro de ambos |
|---:|---:|---:|---:|---:|---:|
| 2023 | 6.758.238 | 2.380 | 9 | 87.272 | 14.872 |
| 2024 | 6.981.102 | 2.207 | 18 | 95.734 | 15.958 |
| 2025 | 6.896.882 | 2.527 | 24 | 102.186 | 17.513 |
| **Total** | **20.636.222** | **7.114** | **51** | **285.192** | **48.343** |

Archivo: `universos_por_anio.csv`.

Cancelados dentro del universo “ambos válidos”: 0 (ya medido históricamente; coherente con nulos de taxi en cancelados).

---

## 3. Horario programado (`CRSDepTime`)

| Clase | Vuelos |
|---|---:|
| HHMM válido (hora 0–23 y minuto 0–59) | 20.928.577 |
| Valor 2400 (medianoche) | 2 |
| Negativos / `>2400` / minuto inválido / 2360–2399 | **0** |

Sobre salidas con `TaxiOut` válido:

| Prueba | Conteo |
|---|---:|
| Grupo 24 con código actual (`//` + 2400→0) | **0** |
| Grupo 24 con HHMM estricto | **0** |
| Grupo 24 con `CAST(CRSDepTime/100 AS INTEGER)` | **59.378** |

**Hallazgo:** el código productivo ya evita el grupo 24. El rango `0..2359` **sí bastaba** en este dataset concreto porque no hay minutos >59; aun así, la auditoría usa la regla estricta de minuto 0–59 como control. `CRSDepTime` es hora **programada**, no la hora efectiva del rodaje; la zona horaria conceptual es la local del aeropuerto según BTS (verificación documental primaria pendiente en fase 3/6).

---

## 4. Desviados y aeropuerto de llegada real

| Medida | Valor |
|---|---:|
| `Diverted=1` | 53.309 |
| Con `Div1Airport` no nulo | 53.309 (100 %) |
| `Dest = Div1Airport` | **0** |
| `Dest ≠ Div1Airport` | **53.309 (100 %)** |
| Desviados con `TaxiIn` ≤180 | 48.347 |
| Desviados en universo ambos válidos | 48.343 |
| Minutos `TaxiIn` válido de desviados | 551.875 |
| CO₂ escenario bajo de ese `TaxiIn` | **10.463,55 t** |

El código actual (`calcular_co2.py`, CTE `llegada`) atribuye `TaxiIn` al campo **`Dest`**. En desviados, `Dest` es el destino programado y `Div1Airport` es el aeropuerto de la primera desviación (aterrizaje real reportado). **Hoy, esas ~10.464 t se cargan al aeropuerto programado, no al de aterrizaje real.**

Ejemplos de pares (archivo `desviados_dest_vs_div1_top.csv`): MCO→TPA, DEN→COS, DFW→OKC/AUS/IAH, ORD→IND/MKE.

### Criterio propuesto (no implementado; requiere aprobación)

1. Si `Diverted ≠ 1`: atribuir `TaxiIn` a `Dest`.
2. Si `Diverted = 1` y `Div1Airport` no nulo: atribuir `TaxiIn` a `Div1Airport`.
3. Si faltara `Div1Airport`: no atribuir geográficamente; conservar el minuto solo en totales no geográficos o marcar categoría `llegada_sin_aeropuerto_confirmado`.

---

## 5. Cruce de clima

| Medida | Valor |
|---|---:|
| Filas clima | 21.920 |
| Aeropuertos | 20 |
| Duplicados `Origin/Fecha` | **0** |
| Max filas por día | 1 (sin multiplicación 1:N) |
| Salidas válidas con clima | 10.570.213 / 20.643.336 = **51,20 %** |
| Salidas válidas sin clima | 10.073.123 |

Umbrales `LLUVIA_FUERTE_MM=5` y `VIENTO_FUERTE_KMH=40`: están en código; **no hay fuente primaria en el repo**. El clima es **diario**, no a la hora del vuelo. Asociación ≠ causalidad.

---

## 6. Borrador de conciliación entre universos publicados

Archivo: `conciliacion_universos.csv`.

| Universo | Observaciones / vuelos | CO₂ bajo (t) |
|---|---:|---:|
| A. Ambos tiempos válidos (`resumen_global`) | 20.636.222 vuelos | **10.303.625,339** |
| B. Solo salida válida | 20.643.336 obs. | 7.042.250,744 |
| C. Solo llegada válida | 20.636.273 obs. | 3.264.397,008 |
| B + C (tramos) | **41.279.609** | 10.306.647,752 |
| D. Salida + hora código actual (Dask / panel hora) | 20.643.336 | 7.042.250,744 |

Diferencias cuantificadas:

1. **(B+C) − A en CO₂ = 3.022,413 t**  
   Causada por los ~7.114 vuelos con solo salida válida y ~51 con solo llegada válida (y cualquier asimetría de minutos). El total de tramos **no** es el total global de vuelos con ambos tiempos.
2. **KPI 41.279.609** = tramos B+C, **no** vuelos únicos. Debe etiquetarse como *tramos de rodaje válidos* (o equivalente), no como “operaciones/vuelos”.
3. **Dask 7.042.250,7 t** concilia con el universo de salida con hora, **no** con los 10,3 Mt globales.
4. **Ahorro −10 %** usa A; **ahorro mediana** usa B (aeropuertos grandes). No son sumables entre sí ni contra el mismo denominador sin aclaración.

### Minutos promedio ~13,17 (riesgo de etiqueta)

Si alguien divide minutos totales de tramos por 41.279.609 observaciones, obtiene un promedio **por tramo** (salida o llegada por separado), no minutos totales por vuelo. Un vuelo con ambos tiempos promedia cerca de `17,99 + 8,35 ≈ 26,3` min de rodaje combinado. **Hay que renombrar el KPI** cuando se audite el SQL vivo de Grafana (fase 5).

---

## 7. Clasificación de hallazgos

### Errores demostrados

1. Atribución de `TaxiIn` de desviados a `Dest` cuando `Div1Airport` existe y es distinto (100 % de 53.309; ~10.464 t).
2. Mezcla de universos en narrativa/KPI si se presentan 10,3 Mt, 7,0 Mt y 41,3 M “operaciones” sin definir denominador.
3. Las dos filas de `escenario_ahorro` no comparten el mismo universo de referencia (global vs salida).

### Riesgos por confirmar

- SQL exacto de los paneles desplegados en Grafana Cloud (el JSON del repo no incluye el KPI de operaciones).
- Fuentes primarias de 6/12 kg/min, 3.16 y umbrales climáticos (fase 3).
- Si `Div1Airport` es siempre el aeropuerto del `TaxiIn` reportado (supuesto razonable, no verificado contra diccionario BTS en esta fase).

### Mejoras opcionales

- Documentar HHMM estricto aunque hoy no haya minutos inválidos.
- Separar en el informe “estimación de emisiones” vs “inventario medido”.
- Versionar resultados (`v2/`) antes de regenerar.

---

## 8. Decisiones metodológicas a aprobar antes de la fase 2

No se implementó ninguno de estos cambios.

| # | Decisión | Opciones | Impacto esperado |
|---|---|---|---|
| D1 | Población principal del CO₂ total | **A)** Mantener ambos tiempos (actual, 20.636.222). **B)** Reportar tramos salida/llegada como principal y ambos como secundario. | Etiquetas y, si cambia la fórmula, totales |
| D2 | Atribución de desviados | **A)** `Div1Airport` cuando `Diverted=1`. **B)** Excluir desviados de rankings geográficos. **C)** Dejar `Dest` (actual) y declarar la limitación. | Rankings de llegada; ~10.464 t se mueven de aeropuerto |
| D3 | Tope 180 | **A)** Mantener. **B)** Sensibilidad en anexo sin cambiar el principal. | ≤0,01 % del CO₂ si se incluyen extremos |
| D4 | KPI operaciones / 13,17 min | Renombrar a tramos / promedio por tramo; publicar aparte vuelos únicos | Solo etiquetas si no se cambia el SQL de agregación |
| D5 | Escenarios de ahorro | Recalcular cada uno con referencia explícita del mismo universo; no sumar intervenciones | Texto y tabla `escenario_ahorro` |
| D6 | Parámetros 6 / 12 / 3.16 | **No cambiar** hasta fase 3 con fuentes primarias | — |

---

## 9. Plan priorizado (post-aprobación)

| Prioridad | Cambio | Archivos | Riesgo | Validación |
|---|---|---|---|---|
| 1 | Definiciones y conciliación por año | `docs/auditoria/02_*.md` + posible refactor de agregados | Medio | Tabla A/B/C/D por año |
| 2 | Atribución desviados (si se aprueba D2-A) | `calcular_co2.py`, notebook, informe | Medio-alto en rankings llegada | Diff de CO₂ por aeropuerto |
| 3 | Etiquetas KPI / ahorro | Grafana SQL, `escenario_ahorro`, docs | Bajo | Comparar conteos |
| 4 | Factores científicos | `docs/auditoria/03_*.md` | Alto si se cambian tasas | No tocar 6/12/3.16 sin evidencia |
| 5 | RDS/Grafana/staging | `subir_resultados_aws.py`, paneles | Alto operativo | Staging + dry-run |

---

**Fin de fases 0 y 1.** Esperando aprobación de D1–D6 (o un subconjunto) para iniciar la fase 2. No se modificaron datos productivos ni parámetros del modelo.
