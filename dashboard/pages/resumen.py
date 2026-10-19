"""Página 1: cifras globales, ranking de aeropuertos y evolución mensual."""
import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go

from servicios import datos

dash.register_page(__name__, path="/", name="Resumen", order=0)


def tarjeta(titulo, id_):
    return dbc.Card(dbc.CardBody([html.Small(titulo, className="text-muted"),
                                  html.H3(id=id_, className="mb-0")]))


layout = html.Div([
    dbc.Row([
        dbc.Col(tarjeta("Movimientos (salidas + llegadas)", "kpi-vuelos"), md=3),
        dbc.Col(tarjeta("Horas de rodaje", "kpi-horas"), md=3),
        dbc.Col(tarjeta("CO2 (toneladas)", "kpi-co2"), md=3),
        dbc.Col(tarjeta("CO2 evitable bajando 10 % el rodaje (t)", "kpi-ahorro"), md=3),
    ], className="mb-2 g-3"),
    html.Small("Cifras por tramo: salida y llegada se cuentan por separado "
               "(41,3 M tramos; 10.306.648 t en el escenario bajo). El total global "
               "del informe, 10.303.625 t, usa solo vuelos con ambos tiempos válidos "
               "(ver docs/auditoria/02_decisiones_metodologicas.md, D1).",
               className="text-muted d-block mb-3"),
    dbc.Row([
        dbc.Col(dcc.Graph(id="g-top"), md=6),
        dbc.Col(dcc.Graph(id="g-mes"), md=6),
    ]),
])


@callback(
    Output("kpi-vuelos", "children"), Output("kpi-horas", "children"),
    Output("kpi-co2", "children"), Output("kpi-ahorro", "children"),
    Output("g-top", "figure"), Output("g-mes", "figure"),
    Input("f-anios", "value"), Input("f-tipo", "value"), Input("f-escenario", "value"),
)
def actualizar(anios, tipos, escenario):
    if not anios or not tipos:
        return "—", "—", "—", "—", go.Figure(), go.Figure()

    df = datos.filtrar_mes(anios, tipos, escenario)
    co2 = df.co2_t.sum()

    top = (df.groupby("aeropuerto", as_index=False).co2_t.sum()
             .nlargest(15, "co2_t").sort_values("co2_t"))
    fig_top = px.bar(top, x="co2_t", y="aeropuerto", orientation="h",
                     title="Top 15 aeropuertos por CO2 de rodaje",
                     labels={"co2_t": "CO2 (t)", "aeropuerto": ""})

    mes = df.groupby("periodo", as_index=False).co2_t.sum()
    fig_mes = px.line(mes, x="periodo", y="co2_t", markers=True,
                      title="CO2 de rodaje por mes",
                      labels={"co2_t": "CO2 (t)", "periodo": ""})

    return (datos.formato(df.vuelos_sel.sum()),
            datos.formato(df.horas_sel.sum()),
            datos.formato(co2),
            datos.formato(co2 * 0.10),  # el CO2 es lineal en los minutos
            fig_top, fig_mes)
