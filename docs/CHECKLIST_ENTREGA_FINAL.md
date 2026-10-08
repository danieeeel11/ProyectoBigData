# Checklist de entrega final — Rodaje y CO₂

Fecha de actualización: 8 de octubre de 2026.

## Hecho en repositorio

- [x] Universo principal documentado (20.636.222; 10.303.625 / 20.607.251 t)
- [x] D2 documentado: no reatribuir a `Div1Airport`
- [x] D4 etiquetas de tramos / promedio por tramo en informe y `docs/grafana_paneles.md`
- [x] Nota de sensibilidad D5 (−690 t; 0,07 %) en informe; CSV de ahorro **no** regenerado
- [x] Auditoría fases 0–1 en `docs/auditoria/`
- [x] Notebook EDA, Prefect, Dask, scripts CO₂
- [x] Evidencias locales en `data/evidencia/` (Prefect, Dask A/B)

## Manual — AWS / Grafana (hoy)

- [ ] Renombrar en el tablero vivo (si existen) los títulos a:
  - `Tramos de rodaje válidos (salidas + llegadas)`
  - `Tiempo promedio por tramo de rodaje`
- [ ] **No** recargar RDS por D5 (pospuesto)
- [ ] Verificar que el KPI de CO₂ total siga en ~10.303.625 t (escenario bajo)
- [ ] Capturar paneles con etiquetas correctas

## Manual — Documento y docente

- [ ] Revisar `informe_rodaje_co2.docx` (textos D2/D4/D5 ya insertados)
- [ ] Pasar/actualizar Google Docs o Word colaborativo
- [ ] Compartir con **rodolfo.meza@gmail.com** como **editor**
- [ ] Pegar capturas Prefect / Dask / AWS / Grafana
- [ ] Completar referencia ICAO 3,16 el día de consulta

## Manual — GitHub

- [ ] Subir textos/docs/informe (sin `.env`, sin `data/raw`, sin Parquet)
- [ ] No subir el dataset original

## No hacer hoy

- Regenerar `escenario_ahorro.csv`
- Cambiar 6 / 12 / 3.16
- Reatribuir desviados
- Modelos predictivos nuevos
