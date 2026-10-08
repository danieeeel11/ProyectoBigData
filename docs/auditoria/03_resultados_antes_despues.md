# Fase 2 — Antes / después (textos; sin recálculo productivo D5)

Fecha: 8 de octubre de 2026.  
Backup: `data/resultados/_backup_textos_fase2_20261008_152601/`.

## Cifras numéricas de resultados productivos

| Indicador | Antes | Después | ¿Cambió el número? |
|---|---:|---:|---|
| CO₂ global bajo | 10.303.625 t | 10.303.625 t | No |
| CO₂ global alto | 20.607.251 t | 20.607.251 t | No |
| Vuelos ambos válidos | 20.636.222 | 20.636.222 | No |
| Tramos válidos | 41.279.609 | 41.279.609 | No (solo etiqueta) |
| Promedio por tramo | 13,17 min | 13,17 min | No (solo etiqueta) |
| Ahorro −10 % publicado | 1.030.363 t | 1.030.363 t | No |
| Ahorro mediana publicado | 1.007.869 t | 1.007.869 t | No (D5 pospuesto) |
| Sensibilidad mediana (ambos válidos) | no estaba en informe | **1.007.179 t** (−690 t; 0,07 %) | Solo nota documental |
| `escenario_ahorro.csv` | intacto | intacto | No regenerado |
| RDS | — | — | No tocado |

## Textos / etiquetas

| Elemento | Antes | Después |
|---|---|---|
| KPI 41.279.609 | “operaciones” / ambigua | **Tramos de rodaje válidos (salidas + llegadas)** |
| KPI 13,17 | “tiempo promedio” ambiguo | **Tiempo promedio por tramo de rodaje** |
| Desviados en informe | 48.343 sin matizar `DivReachedDest` | 48.343 ambos válidos + explicación 48.347 / 14 / 4.948 |
| Atribución `TaxiIn` | implícita a `Dest` | Explícita: no usar `Div1Airport`; justificado |
| Producto del análisis | “inventario de CO2” | “estimación de CO2 por rodaje” |
| Factores 6/12 | mezcla de referencia/validar | escenarios hipotéticos de sensibilidad |

## Archivos tocados en esta pasada

- `informe_rodaje_co2.docx`
- `docs/informe_borrador.md`
- `docs/grafana_paneles.md` (sección de etiquetas KPI)
- `docs/auditoria/02_decisiones_metodologicas.md`
- `docs/auditoria/03_resultados_antes_despues.md` (este archivo)
- `docs/CHECKLIST_ENTREGA_FINAL.md`

No modificados: `config.py`, Parquet, rankings, Dask, `escenario_ahorro.csv`, RDS, `grafana_dashboard.json` (no contenía esos KPI).
