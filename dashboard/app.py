"""Dashboard Dash: rodaje en tierra, combustible y CO2 (BTS 2023-2025).

Estructura:
    app.py        crea la aplicación, la barra, los filtros y arranca el servidor
    servicios/    lectura de las tablas de data/resultados
    pages/        una página por archivo; Dash las registra solas
"""
import dash
from dash import Dash, dcc
import dash_bootstrap_components as dbc

from servicios import datos

ANIOS = sorted(datos.por_mes().anio.unique().tolist())

app = Dash(__name__, use_pages=True,
           external_stylesheets=[dbc.themes.FLATLY],
           title="Rodaje y CO2 · BTS")
server = app.server  # servidor Flask, por si se publica con gunicorn

barra = dbc.NavbarSimple(
    [dbc.NavItem(dbc.NavLink(p["name"], href=p["relative_path"]))
     for p in sorted(dash.page_registry.values(), key=lambda p: p["order"])],
    brand="Rodaje en tierra y CO2 · BTS 2023-2025",
    color="primary", dark=True, className="mb-3",
)

filtros = dbc.Card(dbc.CardBody(dbc.Row([
    dbc.Col([dbc.Label("Años"),
             dcc.Dropdown(id="f-anios", options=ANIOS, value=ANIOS,
                          multi=True, clearable=False)], md=4),
    dbc.Col([dbc.Label("Tipo de rodaje"),
             dcc.Checklist(id="f-tipo",
                           options=[{"label": "Salida (TaxiOut)", "value": "salida"},
                                    {"label": "Llegada (TaxiIn)", "value": "llegada"}],
                           value=["salida", "llegada"], inline=True,
                           inputClassName="me-1", labelClassName="me-3")], md=4),
    dbc.Col([dbc.Label("Escenario de consumo"),
             dcc.RadioItems(id="f-escenario",
                            options=[{"label": "Bajo (6 kg/min)", "value": "bajo"},
                                     {"label": "Alto (12 kg/min, por validar)", "value": "alto"}],
                            value="bajo", inline=True,
                            inputClassName="me-1", labelClassName="me-3")], md=4),
])), className="mb-3")

app.layout = dbc.Container([barra, filtros, dash.page_container], fluid=True)

if __name__ == "__main__":
    app.run(debug=True, port=8050)
