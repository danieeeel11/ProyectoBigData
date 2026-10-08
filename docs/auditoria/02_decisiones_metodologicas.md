# Fase 2 — Decisiones metodológicas (aprobadas y aplicadas en texto)

Fecha: 8 de octubre de 2026.

## Resumen de aprobación

| Decisión | Resolución | Estado de implementación |
|---|---|---|
| D1 | Universo principal ambos tiempos; totales 10.303.625 / 20.607.251 t | Documentado; cifras globales sin cambio |
| D2 | Solo documentar; **no** reatribuir `Dest`→`Div1Airport` | Documentado en informe y auditoría |
| D3 | Mantener tope 180 | Sin cambio de código |
| D4 | Renombrar KPI a tramos / promedio por tramo | Textos informe + `docs/grafana_paneles.md` |
| D5 | **Pospuesto** recálculo productivo; nota de sensibilidad −690 t (0,07 %) | Nota en informe; `escenario_ahorro.csv` intacto |
| D6 | Mantener 6 / 12 / 3.16; lenguaje de estimación | Texto de supuestos actualizado |

## D2 — Evidencia (consultas del 8/10/2026)

- `TaxiIn` válido en desviados: **48.347**, todos con `DivReachedDest=1`.
- Ambos tiempos válidos en desviados: **48.343** (4 tienen `TaxiOut>180`).
- Total desviados **53.309** = 48.361 alcanzaron Dest + 4.948 no alcanzaron.
- De los 48.361 que alcanzaron Dest: 48.347 con `TaxiIn`≤180 + **14** sin `TaxiIn` válido (3 nulos, 11 >180).
- Conclusión: atribución a `Dest` coherente; no se cambia el código.

## D4 — Verificación del promedio 13,17

- Tramos: 20.643.336 + 20.636.273 = **41.279.609**
- Minutos: 371.426.727 (salida) + 172.172.838 (llegada) = **543.599.565**
- Promedio: 543.599.565 / 41.279.609 = **13,1687 → 13,17 min**

## D5 — Sensibilidad (sin regenerar CSV)

Cálculo publicado (población de salidas): 1.007.869 t evitadas.  
Mismo criterio sobre ambos tiempos válidos: 1.007.179 t (−690 t, 0,07 %).  
RDS y `escenario_ahorro.csv` **no** se modificaron.
