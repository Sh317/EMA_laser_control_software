import dash
from dash import dcc, html, Input, Output, State, set_props
import dash_bootstrap_components as dbc
import sys
import os
import time
import traceback
import plotly.graph_objects as go

# sys.path.append('.\\src')
# from control.st_laser_control import LaserControl

state = {
    'etalon_lock': True,
    'etalon_tuner_value': 0.0,
    'cavity_lock': True,
    'cavity_tuner_value': 0.0,
    'target_default': 0.0,
    'freq_lock_clicked': False,
    'kp_enable': True,
    'ki_enable': True,
    'kd_enable': True,
    'kp_default': 0.0,
    'ki_default': 0.0,
    'kd_default': 0.0
}

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

def get_etalon_lock_status():
    """Gets etalon lock status, returns corresponding boolean value, and raises an error if there is lock error
    
    Return:
        bool: True if etalon lock is on and false otherwise.
    """
    e_status = control_loop.etalon_lock_status
    assert isinstance(e_status, str) and e_status in ["on", "off"], f"Invalid etalon lock status: {e_status}"
    return True if  e_status == "on" else False

def get_cavity_lock_status():
    """Gets cavity lock status, returns corresponding boolean value, and raises an error if there is lock error
    
    Return:
        bool: True if cavity lock is on and false otherwise.
    """
    c_status = control_loop.reference_cavity_lock_status
    assert isinstance(c_status, str) and c_status in ["on", "off"], f"Invalid cavity lock status: {c_status}"
    return True if  c_status == "on" else False

def error(error, header, icon):
    set_props('toast', {'header': f'{header}', 'children': f"Error: {error} \n {traceback.format_exc()}", 'icon': f'{icon}'})




# patient_netconnect()
# reading_rate = get_rate()
reading_rate = 0.1



app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX, dbc.icons.FONT_AWESOME])

colors = {'sidebar_bg': "#D3D3D3",
          'main_bg': "#f8f9fa",
          'value': "#FA8128",
          'label': "#00008B",
          'status_inactive': "#9c9c9f",
          'status_active': "#f0ad4e",
          }

text_style = {'sub_header': {'fontSize': '18px','fontWeight': 'bold','padding': '14px 0'},
              'label': {'fontSize': '14px','fontWeight': 'bold', 'color': colors['label']}}

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

tab1_content = dbc.Container([
    html.H4("SolsTis Control", style=text_style['sub_header']),
    
    dbc.Row([
        dbc.Col(dcc.Markdown("**Etalon**", style=text_style['label']), width=3,),
        dbc.Col(dbc.Button(html.I(className='fa-solid fa-lock fa-fw', id='etalon_lock_icon',), id='etalon_lock_button', outline=True, color='info'), width=3,),
        dbc.Col(dcc.Input(id='etalon_tuner', type='number', value=state['etalon_tuner_value'], step=0.00001), width=6,),
    ], align='center', justify='evenly'),

    html.Br(),

    dbc.Row([
        dbc.Col(dcc.Markdown("**Cavity**", style=text_style['label']), width=3),
        dbc.Col(dbc.Button(html.I(className='fa-solid fa-lock fa-fw', id='cavity_lock_icon',), id='cavity_lock_button', outline=True, color='info'), width=3,),
        dbc.Col(dcc.Input(id='cavity_tuner', type='number', value=state['cavity_tuner_value'], step=0.0001), width=6),
    ], align='center', justify='evenly'),

    html.Br(),

    html.H4("Wavelength Locker", style=text_style['sub_header'], className="mb-4"),
    
    dbc.Row([
        dbc.Col(dcc.Markdown("Target Wavenumber", style=text_style['label']), width=3,),
        dbc.Col(dcc.Input(id='t_wnum', type='number', value=state['target_default'], step=0.00001), width=5,),
        dbc.Col(dbc.Button('Lock  ', id='freq_lock_button', outline=True, color='info',style={'width': '70%'}), width=4),
    ], class_name = 'mb-4', align='bottom', justify='evenly'),

    dbc.Row([
        dbc.Col(dcc.Markdown("*_Wavelength Not Locked_*", id="wavelength_locker_status", style={'color': colors['status_inactive'], 'font-weight': 'bolder'}), width=8),
        dbc.Col(dbc.Button('Unlock', id='freq_unlock_button', outline=True, disabled=True, color='info',style={'width': '70%', 'textAlign': 'center','justifyContent': 'center', 'display': 'flex',}), width=4),
    ], align='bottom', justify='evenly', class_name='d-flex align-items-center mb-3'),

    html.H4("PID Control", style=text_style['sub_header']),
    
    dbc.Row([
        dbc.Row([
            dbc.Col([dcc.Slider(id='kp', min=0, max=100, step=0.1, marks={0: {'label':'0', 'style': {'color': colors['label']}}, 100: {'label':'100', 'style': {'color': colors['label']}}}, value=state['kp_default'], tooltip={"placement": "bottom", "always_visible": True,})],width=8),
            dbc.Col([dbc.Switch(id='kp_enable', label = 'p', label_style = {'color': colors['label']})], width=4)],
            align='center', justify='start', class_name='d-flex align-items-center mb-4'
        ),

        dbc.Row([
            dbc.Col(dcc.Slider(id='ki', min=0, max=10, step=0.1, marks={0: {'label':'0', 'style': {'color': colors['label']}}, 10: {'label':'10', 'style': {'color': colors['label']}}}, value=state['ki_default'], tooltip={"placement": "bottom", "always_visible": True,}), width=8,),
            dbc.Col([dbc.Switch(id='ki_enable', label = 'i', label_style = {'color': colors['label']})], width=4)],
            align='center', justify='start', class_name='d-flex align-items-center mb-4'
        ),
        
        dbc.Row([
            dbc.Col(dcc.Slider(id='kd', min=0, max=10, step=0.1, marks={0: {'label':'0', 'style': {'color': colors['label']}}, 10: {'label':'10', 'style': {'color': colors['label']}}}, value=state['kd_default'], tooltip={"placement": "bottom", "always_visible": True,}), width=8,),
            dbc.Col([dbc.Switch(id='kd_enable', label = 'd', label_style = {'color': colors['label']})], width=4)],
            align='center', justify='start', class_name='d-flex align-items-center mb-4'
        ),
    ]),

    dbc.Row(dbc.Col(dbc.Button('Update', id='pid_update_button', color='info', outline=True), width=6)),
])

tab1 =  dcc.Tab(children=tab1_content, label='Control', value='tab-1',)
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
        dbc.Col(sidebar, width=5, style={"background-color": colors['sidebar_bg']}),
        dbc.Col([
            dbc.Row([plot], style={'size': 8, 'offset': 2, "display": "flex", "justify-content": "center",},),
            html.Br(),
            dbc.Row(
                [
                    dbc.Col(html.Div([dcc.Markdown("*Current Wavenumber(cm^-1)*", style={'font-size': '12px', 'color': colors['label'], 'text-align': 'center'}), 
                             dcc.Markdown('anything', id='wnum_display', style={'font-size': '24px', 'font-weight': 'bold', 'text-align': 'center', 'color': colors['value'],})],
                             style={'display': 'inline-block',},) 
                            ),
                    dbc.Col(html.Div([dcc.Markdown("*Reading rate(s)*", style={'font-size': '12px', 'color': colors['label'], 'text-align': 'center'}), 
                             dcc.Markdown(f'{reading_rate}', style={'font-size': '24px', 'font-weight': 'bold', 'text-align': 'center', 'color': colors['value'],})],
                             style={'display': 'inline-block',},)
                             )
                ], justify = 'center')
                ],style={"background-color": colors['main_bg'],}),
        ], style={'display': 'flex', 'height': '100vh'},),
    toast,
    refresher
], fluid=True)

@app.callback(
    Output('etalon_lock_icon', 'className'),
    Input('etalon_lock_button', 'n_clicks'),
)
def lock_etalon(n_clicks):
    """Lock etalon if it's unlocked and unlock otherwise"""
    for tries in range(2):
        try:
            # if get_etalon_lock_status():
            #     control_loop.unlock_reference_etalon()
            #     return 'fa-solid fa-lock-open fa-fw'
            # else:
            #     control_loop.lock_reference_etalon()
            #     return 'fa-solid fa-lock fa-fw'
            if state['etalon_lock']:
                state['etalon_lock'] = False
                print('Etalon unlocked')
                return 'fa-solid fa-lock-open fa-fw'
            else:
                state['etalon_lock'] = True
                print('Etalon locked')
                return 'fa-solid fa-lock fa-fw'
        except Exception as e:
            if tries >= 2:
                error(e, 'Error in locking etalon', 'warning')
                break
            tries += 1
            print(f"Error in locking etalon: {e}")
            time.sleep(0.5)

@app.callback(
        output=Output('cavity_lock_icon', 'className'),
        inputs=Input('cavity_lock_button', 'n_clicks'),
)
def lock_cavity(n_clicks):
    """Lock cavity if it's unlocked and unlock otherwise"""
    for tries in range(2):
        try:
            # if get_cavity_lock_status():
            #     control_loop.unlock_reference_cavity()
            #     return 'fa-solid fa-lock-open fa-fw'
            # else:
            #     control_loop.lock_reference_cavity()
            #     return 'fa-solid fa-lock fa-fw'
            if state['cavity_lock']:
                state['cavity_lock'] = False
                print('Cavity unlocked')
                return 'fa-solid fa-lock-open fa-fw'
            else:
                state['cavity_lock'] = True
                print('Cavity locked')
                return 'fa-solid fa-lock fa-fw'
        except Exception as e:
            if tries >= 2:
                error(e, 'Error in locking reference cavity', 'warning')
                break
            tries += 1
            print(f"Error in locking cavity: {e}")
            time.sleep(0.5)

# @app.callback(
#     [Output('wavenumber_vs_time', 'figure'),
#      Output('wnum_display', 'children')],
#     Input('interval-component', 'n_intervals'))
# def update_plot(n_intervals):
#     """Loop function that updates the current wavenumber and plot continuously in the while loop
    
#     Args:
#         plot(placeholder): Placeholder for the plot
#         dataf_space(placeholder: Placeholder for the current wavenumber)
#     """
#     try:
#         xtoPlot, ytoPlot = control_loop.get_df_to_plot()
#         control_loop.update()
#         c_wnum = get_cwnum()
#         c_wnum = str(c_wnum)
#     except Exception as e:
#         error(e, 'Error in getting plot data', 'warning')
#     # Time series plot
#     if xtoPlot and ytoPlot:
#         fig = go.Figure(data=go.Scatter(x=xtoPlot, y=ytoPlot, mode='lines+markers', marker=dict(size = 8, color='rgba(255,77,1, 1)')), layout=go.Layout(
#             xaxis=dict(title="Time(s)"), yaxis=dict(title="Wavenumber (cm^-1)", exponentformat="none"), uirevision=True, paper_bgcolor=colors['main_bg'], plot_bgcolor=colors['sidebar_bg'],  
#             ))
#         fig.update_xaxes(showgrid=True, gridwidth=1, griddash='dash', minor_griddash="dot", gridcolor='Blue')
#         # if state.freq_lock_clicked or state.scan_button:
#         #     y_ref = control_loop.target
#         #     y_lower = y_ref - 0.00002
#         #     y_upper = y_ref + 0.00002
#         #     fig.add_hrect(y0=y_lower, y1=y_upper, line_width=0, fillcolor="LightPink", opacity=0.5)

#     # dataf_space.metric(label="Current Wavenumber", value=state.c_wnum)
#     return fig, c_wnum

def main():
    try:
        app.run(debug=True, dev_tools_hot_reload=False)
    except KeyboardInterrupt:
        control_loop.stop()
        print(1)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=2355)
