"""Página 2: franjas horarias del rodaje de salida.

co2_aeropuerto_hora.csv solo trae el rodaje de SALIDA (TaxiOut) y suma los
tres años, así que en esta página solo aplica el filtro de escenario.
"""
import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px

from servicios import datos

dash.register_page(__name__, path="/horas", name="Franjas horarias", order=1)

layout = html.Div([
    dbc.Alert("Esta página usa solo el rodaje de salida (TaxiOut), 2023-2025 sumados. "
              "Aquí solo aplica el filtro de escenario.", color="info"),
    dbc.Row([dbc.Col(dcc.Graph(id="g-hora"), md=12)]),
    dbc.Row([dbc.Col(dcc.Graph(id="g-calor"), md=12)]),
])


@callback(
    Output("g-hora", "figure"), Output("g-calor", "figure"),
    Input("f-escenario", "value"),
)
def actualizar(escenario):
    df = datos.por_hora()
    co2 = f"co2_t_{escenario}"

    hora = df.groupby("hora", as_index=False)[co2].sum()
    fig_hora = px.bar(hora, x="hora", y=co2,
                      title="CO2 del rodaje de salida por hora programada",
                      labels={"hora": "Hora de salida programada", co2: "CO2 (t)"})
    fig_hora.update_xaxes(dtick=1)

    top = df.groupby("aeropuerto")[co2].sum().nlargest(20).index
    tabla = (df[df.aeropuerto.isin(top)]
               .pivot_table(index="aeropuerto", columns="hora",
                            values="min_promedio_salida")
               .reindex(top))
    fig_calor = px.imshow(
        tabla, aspect="auto", color_continuous_scale="Reds",
        labels={"x": "Hora programada", "y": "", "color": "Min/vuelo"},
        title="Minutos promedio de rodaje de salida · top 20 aeropuertos por CO2")
    fig_calor.update_layout(height=650)
    fig_calor.update_xaxes(dtick=1)
    return fig_hora, fig_calor
