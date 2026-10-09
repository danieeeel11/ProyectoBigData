# Fase 2 — Decisiones metodológicas (con evidencia D2)

Fecha: 8 de octubre de 2026.  
Fuente de datos: Parquet local + CSV de `data/resultados/auditoria/` (no se reejecutó la auditoría completa).  
Estado: **impactos calculados; cambios productivos pendientes de confirmación**.

---

## D1 — Población principal (aprobada)

- Principal: **20.636.222** vuelos con `TaxiOut` y `TaxiIn` no nulos y `≤ 180`.
- Totales a conservar: **10.303.625 t** (6 kg/min) y **20.607.251 t** (12 kg/min).
- Poblaciones secundarias (salida, llegada, hora) se mantienen etiquetadas como tales.
- Diferencia **(salida + llegada) − global ≈ 3.022 t**: no se fuerza igualdad; se documenta (vuelos con un solo tramo válido).

## D2 — Desviados: verificación obligatoria (resultado)

### Campos disponibles (confirmados en esquema)

`Diverted`, `DivReachedDest`, `DivAirportLandings`, `Div1Airport`…`Div5Airport`, `DivActualElapsedTime`, `TaxiIn`, `Dest`.

### Hallazgo clave

| Grupo | Vuelos | Con `TaxiIn` ≤ 180 | CO₂ bajo de ese `TaxiIn` |
|---|---:|---:|---:|
| Desviado y **alcanzó** destino (`DivReachedDest=1`) | 48.361 | **48.347** | **10.463,55 t** |
| Desviado y **no** alcanzó destino (`DivReachedDest=0`) | 4.948 | **0** | **0 t** |

- El 100 % del `TaxiIn` válido de desviados ocurre solo cuando `DivReachedDest = 1`.
- Cuando el vuelo no llega a `Dest`, BTS no reporta `TaxiIn` usable en este universo.
- `Dest ≠ Div1Airport` en todos los desviados: `Div1Airport` es el aeropuerto de la desviación intermedia, no necesariamente donde ocurre el `TaxiIn` final.
- Hay casos con 2–3 aterrizajes que igual alcanzan destino (282 con `TaxiIn` válido); el carreteo final reportado sigue asociado a haber llegado a `Dest`.

### Decisión operativa D2

**No sustituir `Dest` por `Div1Airport`.**  
La atribución actual de `TaxiIn` a `Dest` es coherente con los datos: esas ~10.464 t **no** están demostrablemente mal atribuidas al destino programado cuando el vuelo lo alcanzó.

Incertidumbre residual (documentar, no inventar aeropuerto): BTS no identifica en una sola columna “el aeropuerto exacto del segmento de `TaxiIn`” cuando hubo múltiples aterrizajes; la evidencia disponible apunta a que el `TaxiIn` solo aparece al completar el itinerario hacia `Dest`.

**Cambio de código por D2:** ninguno en agregados geográficos. Solo documentación.

## D3 — Tope 180 (aprobada)

Mantener `TAXI_MAX_MIN = 180`. Sensibilidad ya medida: incluir extremos sumaría ~1.206 t (~0,01 %). No tocar Parquet.

## D4 — Indicadores (impacto verificado)

| Indicador | Cálculo verificado | Valor |
|---|---|---:|
| Tramos de rodaje válidos | obs. salida `TaxiOut`≤180 + obs. llegada `TaxiIn`≤180 | **41.279.609** |
| Minutos en esos tramos | Σ TaxiOut (válido) + Σ TaxiIn (válido) | 543.599.565 |
| Promedio por tramo | minutos / tramos | **13,1687 → 13,17 min** |

El promedio **sí** usa el mismo denominador que el numerador de tramos. No hay que corregir la fórmula; solo las etiquetas:

- «Operaciones / vuelos» → **Tramos de rodaje válidos (salidas + llegadas)**
- «Tiempo promedio» → **Tiempo promedio por tramo de rodaje (min)**

## D5 — Ahorros (impacto propuesto, mismo universo principal)

Ambas intervenciones recalculadas sobre vuelos con **ambos** tiempos válidos. Escenario de consumo: bajo (6 kg/min). **No sumar** las dos intervenciones.

| Intervención | Ref. CO₂ (t) | Min evitados | CO₂ evitado (t) | CO₂ posterior (t) | % reducción | Antes (publicado) |
|---|---:|---:|---:|---:|---:|---:|
| −10 % uniforme | 10.303.625,339 | 54.344.017 | **1.030.362,534** | 9.273.262,805 | 10,00 % | igual (1.030.362,534) |
| Salida lenta → mediana* | 10.303.625,339 | 53.121.230 | **1.007.178,553** | 9.296.446,786 | **9,78 %** | 1.007.868,569 |

\*Mediana de promedios de salida entre aeropuertos con >50.000 vuelos **dentro del universo ambos-válidos**: **15,6859 min** (antes 15,6864 / texto 15,69). Aeropuertos grandes: 76.  
Delta mediana vs publicado: **−690 t** de CO₂ evitado (−0,07 % relativo al ahorro anterior).

Columnas nuevas propuestas en `escenario_ahorro.csv`:  
`concepto, detalle, universo, co2_t_referencia, minutos_evitados, co2_t_evitado, co2_t_posterior, pct_reduccion, nota_no_sumar`.

Conservar el CSV actual como `data/resultados/_backup_.../escenario_ahorro.csv` o `escenario_ahorro_antes_fase2.csv`.

## D6 — Factores (aprobada)

Mantener 6 / 12 / 3.16. Lenguaje: escenarios hipotéticos / estimación, no medición directa. ICAO 3,16 para Jet-A/Jet-A1 con referencia en el informe (fase documental).

---

## Impacto esperado si se confirma la implementación

| Componente | ¿Cambia? | Detalle |
|---|---|---|
| `resumen_global`, top, hora, clima, Dask | No | Totales globales y rankings de salida intactos |
| Atribución desviados / `co2_aeropuerto_mes` llegada | No | D2 no exige corrección |
| `escenario_ahorro.csv` | **Sí** | Recálculo D5 + columnas; delta ≈ −690 t en intervención mediana |
| Docs Grafana / JSON títulos KPI | **Sí (etiquetas)** | D4: renombrar tramos y promedio 13,17 |
| Informe Word | Sí (texto) | Metodología D2/D4/D5, lenguaje de estimación |
| AWS RDS | Solo tabla `escenario_ahorro` tras validar local | No tocar resto |
| Prefect / Dask | Sin cambio de lógica de benchmark | Reejecutar solo si se pide evidencia fresca |
| Parámetros `config.py` | No | D3/D6 |

## Confirmación solicitada

Para aplicar cambios productivos locales (backup + `calcular_co2.py` + regenerar `escenario_ahorro` + actualizar docs de paneles), responda **sí** a:

1. **D2:** documentar únicamente; no reatribuir a `Div1Airport`.  
2. **D4:** renombrar KPI; conservar 41.279.609 y 13,17.  
3. **D5:** regenerar `escenario_ahorro` con el universo principal (delta mediana −690 t).  
4. **AWS:** no subir todavía; preparar staging/recarga solo de `escenario_ahorro` cuando usted lo indique.

Hasta esa confirmación **no** se sobrescriben CSV productivos ni se toca RDS.
