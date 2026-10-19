# Dashboard Dash: rodaje en tierra y CO2

Lee las tablas ya verificadas de `data/resultados/` (no necesita el Parquet).

1. `conda activate bigdata`
2. `pip install dash dash-bootstrap-components plotly`
3. Desde la raíz del repo: `cd dashboard` y `python app.py`
4. Abre http://localhost:8050

Páginas:

- **Resumen**: KPIs, top 15 aeropuertos por CO2 y CO2 mensual. Filtros de año, tipo de rodaje y escenario.
- **Franjas horarias**: CO2 por hora y mapa de calor aeropuerto × hora (solo rodaje de salida).

Si `calcular_co2.py` se vuelve a correr, basta con reiniciar `app.py`.
