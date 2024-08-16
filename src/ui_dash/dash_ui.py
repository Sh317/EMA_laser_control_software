import dash
from dash import dcc, html, Input, Output, State, set_props
import dash_bootstrap_components as dbc
import sys
import os
import wx
import time
import traceback
import plotly.graph_objects as go

sys.path.append('.\\src')
from control.st_laser_control import LaserControl

def patient_netconnect(tryouts=10):
    """Try to instantiate the laser class if this is the first call, otherwise inherit the properties.
    
    Arg:
        tryouts(int): The number of tries to initialize the laser setting. Default is 10 times
    """
    tries = 0
    global control_loop
    while tries <= tryouts:
        try:
            control_loop = LaserControl("192.168.1.222", 39933, "LaserLab:wavenumber_1", verbose=True)
            break
        except Exception as e:
            tries += 1
            if tries >= tryouts:
                print(f"Unable to initialize the laser control after {tryouts} tries.")
                raise ConnectionError
                break
            print(f"Unable to initialize the laser control due to error: {e} \n {traceback.format_exc()}")
            time.sleep(0.5)

def get_rate():
    """Get reading rate"""
    return control_loop.rate

def get_cwnum():
    """Get current wavenumber"""
    return control_loop.get_current_wnum()

def error(error, header, icon):
    set_props('toast', {'header': f'{header}', 'children': f"Error: {error} \n {traceback.format_exc()}", 'icon': f'{icon}'})

patient_netconnect()
reading_rate = get_rate()



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

tab1 =  dcc.Tab(label='Control', value='tab-1', style={"background-color": "#f8f9fa"})
tab2 = dcc.Tab(label='Scan', value='tab-2')
tab3 = dcc.Tab(label='Save', value='tab-3')
sidebar = dcc.Tabs(id='sidebar', value='tab-1', children=[tab1, tab2, tab3],)

plot = dcc.Graph(id='wavenumber_vs_time',)

toast = dbc.Toast(
            "empty",
            id="toast",
            header="",
            is_open=False,
            dismissable=True,
            icon="danger",
            # Options are: "primary", "secondary", "success", "warning", "danger", "info", "light" or "dark".
            style={"position": "fixed", "top": 66, "right": 8, "width": 350},
        )

refresher = dcc.Interval(id='interval-component', interval=1*100, n_intervals=0)

app.layout = dbc.Container(
    [
    title_bar,
    dbc.Row([
        dbc.Col(sidebar, width=5),
        dbc.Col([
            dbc.Row([plot], style={'size': 8, 'offset': 2, "display": "flex", "justify-content": "center"}),
            html.Br(),
            dbc.Row(
                [
                    dbc.Col(html.Div([dcc.Markdown("*Current Wavenumber(cm^-1)*", style={'font-size': '12px', 'color': '#03002e', 'text-align': 'center'}), 
                             dcc.Markdown('1', id='wnum_display', style={'font-size': '24px', 'font-weight': 'bold', 'text-align': 'center', 'color': '#FA8128',})],
                             style={'background-color':'#f0f0f0', 'display': 'inline-block',},) 
                            ),
                    dbc.Col(html.Div([dcc.Markdown("*Reading rate(s)*", style={'font-size': '12px', 'color': '#03002e', 'text-align': 'center'}), 
                             dcc.Markdown(f'{reading_rate}', style={'font-size': '24px', 'font-weight': 'bold', 'text-align': 'center', 'color': '#FA8128',})],
                             style={'background-color':'#f0f0f0', 'display': 'inline-block',},)
                             )
                ], justify='center',)
                ]),
            ]),
    toast,
    refresher
], fluid=True)

@app.callback(
    [Output('wavenumber_vs_time', 'figure'),
     Output('wnum_display', 'children')],
    Input('interval-component', 'n_intervals'))
def update_plot(n_intervals):
    """Loop function that updates the current wavenumber and plot continuously in the while loop
    
    Args:
        plot(placeholder): Placeholder for the plot
        dataf_space(placeholder: Placeholder for the current wavenumber)
    """
    try:
        xtoPlot, ytoPlot = control_loop.get_df_to_plot()
        control_loop.update()
        c_wnum = get_cwnum()
        c_wnum = str(c_wnum)
    except Exception as e:
        error(e, 'Error in getting plot data', 'warning')
        set_props('toast', {'header': 'Error in getting plot data', 'children': f"Error: {e} \n {traceback.format_exc()}"})
    # Time series plot
    if xtoPlot and ytoPlot:
        fig = go.Figure(data=go.Scatter(x=xtoPlot, y=ytoPlot, mode='lines+markers', marker=dict(size = 8, color='rgba(255,77,1, 1)')), layout=go.Layout(
            xaxis=dict(title="Time(s)"), yaxis=dict(title="Wavenumber (cm^-1)", exponentformat="none"), uirevision=True
            ))
        fig.update_xaxes(showgrid=True, gridwidth=1, griddash='dash', minor_griddash="dot", gridcolor='Blue')
        # if state.freq_lock_clicked or state.scan_button:
        #     y_ref = control_loop.target
        #     y_lower = y_ref - 0.00002
        #     y_upper = y_ref + 0.00002
        #     fig.add_hrect(y0=y_lower, y1=y_upper, line_width=0, fillcolor="LightPink", opacity=0.5)

    # dataf_space.metric(label="Current Wavenumber", value=state.c_wnum)
    return fig, c_wnum

def main():
    try:
        app.run(debug=True, dev_tools_hot_reload=False)
    except KeyboardInterrupt:
        control_loop.stop()
        print(1)

if __name__ == "__main__":
    main()
