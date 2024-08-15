import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import sys
import os
import wx
import time
import traceback
import plotly.graph_objects as go

sys.path.append('.\\src')
from control.st_laser_control import LaserControl

# def patient_netconnect(tryouts=10):
#     """Try to instantiate the laser class if this is the first call, otherwise inherit the properties.
    
#     Arg:
#         tryouts(int): The number of tries to initialize the laser setting. Default is 10 times
#     """
#     tries = 0
#     global control_loop
#     while tries <= tryouts:
#         try:
#             control_loop = LaserControl("192.168.1.222", 39933, "LaserLab:wavenumber_1", verbose=True)
#             break
#         except Exception as e:
#             tries += 1
#             if tries >= tryouts:
#                 print(f"Unable to initialize the laser control after {tryouts} tries.")
#                 raise ConnectionError
#                 break
#             print(f"Unable to initialize the laser control due to error: {e} \n {traceback.format_exc()}")
#             time.sleep(0.5)

# the style arguments for the sidebar. We use position:fixed and a fixed width
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 15,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])

title_bar = dbc.Navbar(
        dbc.Container([
            dbc.Row(
                dbc.Col(
                    html.H1("Laser Control Software", className="text-center", style={"font-size": "2rem", "color": "white"}),
                    width=12
                ),
                justify="center",  # Center the title row
                align="center",  # Align vertically
                className="w-100"  # Ensures it takes the full width of the navbar
            ),
        ]),
        color="dark",
        dark=True,
        style={"height": "4rem"}
    )

tab1_content = dbc.Card(
    dbc.CardBody(
        [
            html.P("This is tab 3!", className="card-text"),
            dbc.Button("Click here", color="success"),
        ]
    ),
    className="mt-3",
)
tab2_content = dbc.Card(
    dbc.CardBody(
        [
            html.P("This is tab 1!", className="card-text"),
            dbc.Button("Click here", color="success"),
        ]
    ),
    className="mt-3",
)
tab3_content = dbc.Card(
    dbc.CardBody(
        [
            html.P("This is tab 1!", className="card-text"),
            dbc.Button("Click here", color="success"),
        ]
    ),
    className="mt-3",
)
tabs = dbc.Tabs([dbc.Tab(tab1_content, label="Control"), dbc.Tab(tab2_content, label="Scan"), dbc.Tab(tab3_content, label="Save")], style={'Width':2})

app.layout = dbc.Container([
    title_bar,
    dbc.Row([
        dbc.Col(html.Div([dbc.Col(tabs,),]), width=4),
        dbc.Col(
            dbc.Row(
                [
                    dbc.Col(html.Div("One of three columns")),
                    dbc.Col(html.Div("One of two columns")),
                ])),
                ])
], fluid=True)

def main():
    try:
        #patient_netconnect()
        app.run_server(debug=True)
    except KeyboardInterrupt:
        # control_loop.stop()
        print(1)

if __name__ == "__main__":
    app.run_server(debug=True)
