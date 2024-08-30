import dash
from dash import dcc, html, Input, Output, State, Patch, set_props, ctx, no_update
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import sys
import os
import wx
import json
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
    'centroid_wnum_default': 12351.23351,
    'kp_enable': True,
    'ki_enable': True,
    'kd_enable': True,
    'kp_default': 0.0,
    'ki_default': 0.0,
    'kd_default': 0.0,
    'state': '1'
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

def calculate_scan_progress(progress, total_time):
    """Calculate the progress of the scan and return the percent completed and corresponding text
    
    Args:
        progress(float): Time elapsed in current pass of scan
        total_time(float): Total time needed for one pass of scan
        
    Returns:
        float: Percent completed
        str: Status text displaying percent completed and eta
    """
    percent = round(progress / total_time, 4) * 100
    if percent >= 1:
        percent = 1.
    etc = round((100 - percent) * total_time, 1)
    current_pass = control_loop.current_pass
    current_pass += 1
    progress_text = f"*Pass {current_pass}*: {percent:.2%} %"
    etc_text = f"_Estimated Time of {current_pass} Pass Completion: {etc} sec left_"
    return percent, progress_text, etc_text

def error(error, header, icon):
    set_props("toast", {'header': f'{header}', 'children': f"Error: {error} \n {traceback.format_exc()}", 'icon': f'{icon}', 'is_open': True,})

def raise_toast(header, content, icon):
    set_props("toast", {'header': f'{header}', 'children': f"{content}", 'icon': f'{icon}', 'is_open': True, 'class_name': f'{icon}'})



# patient_netconnect()
# reading_rate = get_rate()
reading_rate = 0.1



app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX, dbc.icons.FONT_AWESOME], suppress_callback_exceptions=True)
# Suppress callback exceptions since tabs are rendered by callbacks

colors = {'sidebar_bg': "#D3D3D3",
          'main_bg': "#f8f9fa",
          'value': "#FA8128",
          'label': "#00008B",
          'status_inactive': "#9c9c9f",
          'status_active': "#f0ad4e",
          'status_warning': "#d9534f",
          'success': "#4bbf73",
          }

text_style = {'sub_header': {'fontSize': '18px','fontWeight': 'bold','padding': '14px 0'},
              'label': {'fontSize': '14px','fontWeight': 'bold', 'color': colors['label']},
              'scan_info': {'fontSize': '16px','font-style': 'italic', 'fontWeight': 'bolder', 'color': colors['label']}
}

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
        dbc.Col(dcc.Input(id='etalon_tuner', type='number', value=state['etalon_tuner_value'], step=0.0001, min=0., debounce=True), width=6,),
    ], align='center', justify='evenly'),

    html.Br(),

    dbc.Row([
        dbc.Col(dcc.Markdown("**Cavity**", style=text_style['label']), width=3),
        dbc.Col(dbc.Button(html.I(className='fa-solid fa-lock fa-fw', id='cavity_lock_icon',), id='cavity_lock_button', outline=True, color='info'), width=3,),
        dbc.Col(dcc.Input(id='cavity_tuner', type='number', value=state['cavity_tuner_value'], step=0.0001, min=0, debounce=True), width=6),
    ], align='center', justify='evenly'),

    html.Br(),

    html.H4("Wavelength Locker", style=text_style['sub_header'], className="mb-4"),
    
    dbc.Row([
        dbc.Col(dcc.Markdown("Target Wavenumber", style=text_style['label']), width=3,),
        dbc.Col(dcc.Input(id='t_wnum', type='number', value=12255.23381, step=0.00001), width=5,),
        dbc.Col(dbc.Button('Lock  ', id='freq_lock_button', outline=True, color='info',style={'width': '70%'}), width=4),
    ], class_name = 'mb-4', align='bottom', justify='evenly'),

    dbc.Row([
        dbc.Col(dcc.Markdown("*_Wavelength Not Locked_*", id="wavelength_locker_status", style={'color': colors['status_inactive'], 'font-weight': 'bolder',}), width=8, class_name='mt-3'),
        dbc.Col(dbc.Button('Unlock', id='freq_unlock_button', outline=True, disabled=True, color='info',style={'width': '70%', 'textAlign': 'center','justifyContent': 'center', 'display': 'flex',}), width=4),
    ],),

    html.H4("PID Control", style=text_style['sub_header']),
    
    dbc.Row([
        dbc.Row([
            dbc.Col([dcc.Slider(id='kp', min=0, max=100, step=0.1, marks={0: {'label':'0', 'style': {'color': colors['label']}}, 100: {'label':'100', 'style': {'color': colors['label']}}}, value=state['kp_default'], tooltip={"placement": "bottom", "always_visible": True,})],width=8),
            dbc.Col([dbc.Switch(id='kp_enable', label = 'p', label_style = {'color': colors['label']}, value=True)], width=4,)],
            align='center', justify='start', class_name='d-flex align-items-center mb-4'
        ),

        dbc.Row([
            dbc.Col(dcc.Slider(id='ki', min=0, max=10, step=0.1, marks={0: {'label':'0', 'style': {'color': colors['label']}}, 10: {'label':'10', 'style': {'color': colors['label']}}}, value=state['ki_default'], tooltip={"placement": "bottom", "always_visible": True,}), width=8,),
            dbc.Col([dbc.Switch(id='ki_enable', label = 'i', label_style = {'color': colors['label']}, value=False)], width=4)],
            align='center', justify='start', class_name='d-flex align-items-center mb-4'
        ),
        
        dbc.Row([
            dbc.Col(dcc.Slider(id='kd', min=0, max=10, step=0.1, marks={0: {'label':'0', 'style': {'color': colors['label']}}, 10: {'label':'10', 'style': {'color': colors['label']}}}, value=state['kd_default'], tooltip={"placement": "bottom", "always_visible": True,}), width=8,),
            dbc.Col([dbc.Switch(id='kd_enable', label = 'd', label_style = {'color': colors['label']}, value=False)], width=4)],
            align='center', justify='start', class_name='d-flex align-items-center mb-4'
        ),
    ]),

    dbc.Row(dbc.Col(dbc.Button('Update', id='pid_update_button', color='info', outline=True), width=6)),
])

tab2_content = dbc.Container([
    html.H4("Scan Settings", style=text_style['sub_header']),

    dbc.Row([
        dbc.Col([
            dbc.Label("Start Wavenumber (cm^-1)", style=text_style['label']),
            dbc.Input(id="start_wnum", type="number", value=state['centroid_wnum_default'], step=0.00001, class_name="p-2", style={'width': '250px', 'font-weight': 'bolder', 'color': colors['label']}),
        ], width=6),
        dbc.Col([
            dbc.Label("End Wavenumber (cm^-1)", style=text_style['label']),
            dbc.Input(id="end_wnum", type="number", value=state['centroid_wnum_default'], step=0.00001, class_name="p-2", style={'width': '250px', 'font-weight': 'bolder', 'color': colors['label']}),
        ], width=6),
    ]),

    html.Br(),
    
    dbc.Row([
        dbc.Col([
            dbc.Label("No. of Steps", style=text_style['label']),
            dbc.Input(id="no_of_steps", type="number", value=5, min=1, max=500, class_name="p-2", style={'width': '250px', 'font-weight': 'bolder', 'color': colors['label']})
        ], width=6),
        dbc.Col([
            dbc.Label("Time per Step (sec)", style=text_style['label']),
            dbc.Input(id="time_per_scan", type="number", value=2.0, step=1, class_name="p-2", style={'width': '250px', 'font-weight': 'bolder', 'color': colors['label']})
        ], width=6),
    ]),

    html.Br(),
    
    dbc.Row([
        dbc.Col([
            dbc.Label("No. of Passes", style=text_style['label']),
            dbc.Input(id="no_of_passes", type="number", value=1, min=1, max=10, class_name="p-2", style={'width': '250px', 'font-weight': 'bolder', 'color': colors['label']})
        ], width=6),
        dbc.Col([
            dbc.Button("Review Scan Settings", id="show_scan_info", color="info", outline=True, class_name="mt-4"),
        ], width=6),

    ]),
    
    html.Br(),

    dbc.Collapse([
        dbc.Card([
        dbc.CardHeader([dbc.Row([dbc.Label("In Hertz?", style=text_style['label'], width='auto'), dbc.Col(dbc.Checkbox(id="in_hertz", value=True))], align='center'),]),
        dbc.CardBody([html.Div(id="scan_info"),])], outline=True, style={'background-color': colors['main_bg'], 'color': colors['label']}),
        ],id="scan_info_collapse", is_open=False, ),

    html.Br(),

    dbc.Row([
        dbc.Col([
            dbc.Button("Start Scan", id="start_scan", color="info", outline=True,),
        ], width=6),
        dbc.Col([
            dbc.Button("Stop Scan", id="stop_scan", color="info", outline=True, disabled=True),
        ], width=6),
    ]),

    html.Br(),

    dbc.Row([
        dbc.Col([
            dcc.Markdown("*_Ready for Scan !_*", id="scan_status", style={'color': colors['success'], 'font-weight': 'bold', 'font-size': '18px',}),
        ], width=6, class_name='mt-4'),
        dbc.Col([
            dbc.Button("Update Time per Step", id="update_time_per_step", color="info", outline=True, disabled=True),
        ], width=6),
    ]),

    html.Br(),

    dbc.Col([
        dbc.Row([
            dbc.Label("Scan Progress", style=text_style['label'])],),
        dbc.Progress(id='scan_progress', value=100, label='0 %'),
        dcc.Markdown("*_Estimated Time of Completion: 0 sec left_*", id="scan_etc", className='mt-2', style={'color': colors['label'], 'font-weight': 'bolder', 'font-size': '14px',})
    ]),
])

tab3_content = dbc.Container([
    html.H4("Save As", style=text_style['sub_header']),

    dbc.Col([
            dbc.Label("File Name", style=text_style['label']),
            dbc.Input(id="file_name", type="text", placeholder="Enter the file name...", class_name="p-2", style={'width': '100%', 'font-weight': 'bolder', 'color': colors['label']}),
        ]),
    
    html.Br(),

    dbc.Row([
        dbc.Col(dbc.Button('Select Directory', id='dir_select_button', outline=True, color='info',style={'width': '70%', 'textAlign': 'center','justifyContent': 'center', 'display': 'flex',}), width=4),
        dbc.Col(dcc.Markdown("", id="dir_status", style={'color': colors['status_inactive'], 'font-weight': 'bolder',}), width=8, class_name='mt-3'),
        ]),
    
    html.Br(),

    dbc.Row([
        dbc.Col(dbc.Button('Start Saving Data', id='save_button', outline=True, color='info',style={'width': '70%', 'textAlign': 'center','justifyContent': 'center', 'display': 'flex',}), width=6),
        dbc.Col(dbc.Button('Stop Saving Data', id='stop_save_button', disabled=True, outline=True, color='info',style={'width': '70%', 'textAlign': 'center','justifyContent': 'center', 'display': 'flex',}), width=6),
        ])
    ])

sidebar = dcc.Tabs(id='sidebar', value='tab-1', children=[dcc.Tab(tab1_content, label='Control', value='tab-1',), dcc.Tab(tab2_content, label='Scan', value='tab-2'), dcc.Tab(tab3_content, label='Save', value='tab-3')],)

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

refresher = dcc.Interval(id='fast-interval', interval=1*100, n_intervals=0)
refresher_slow = dcc.Interval(id='slow-interval', interval=5*100, n_intervals=0)

app.layout = dbc.Container(
    [
    dcc.Store(id='memory'),
    title_bar,
    dbc.Row([
        dbc.Col([sidebar, html.Div(id='tabs-content')], width=5, style={"background-color": colors['sidebar_bg']}),
        dbc.Col([
            dbc.Row([plot], style={'size': 8, 'offset': 2, "display": "flex", "justify-content": "center",},),
            html.Br(),
            dbc.Row(
                [
                    dbc.Col(html.Div([dcc.Markdown("*Current Wavenumber(cm^-1)*", style={'font-size': '12px', 'color': colors['label'], 'text-align': 'center'}), 
                             dcc.Markdown('12255.23381', id='wnum_display', style={'font-size': '24px', 'font-weight': 'bold', 'text-align': 'center', 'color': colors['value'],})],
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
    refresher,
    refresher_slow,
], fluid=True)

# @app.callback(
#     Output('tabs-content', 'children'),
#     Input('sidebar', 'value'),)
# def render_tab_content(tab):
#     if tab == 'tab-1':
#         return tab1_content
#     elif tab == 'tab-2':
#         return tab2_content
#     elif tab == 'tab-3':
#         return tab3_content

@app.callback(
    Output("scan_info_collapse", "is_open"),
    Input("show_scan_info", "n_clicks"),
    State("scan_info_collapse", "is_open"),
    prevent_initial_call=True,
)
def render_scan_review(n_clicks, is_open):
    return True if not is_open else False

@app.callback(
    Output("scan_info", "children"),
    Input("show_scan_info", "n_clicks"),
    Input("in_hertz", "value"),
    Input("start_wnum", "value"), 
    Input("end_wnum", "value"), 
    Input("no_of_steps", "value"), 
    Input("time_per_scan", "value"),
    Input("no_of_passes", "value"), 
    prevent_initial_call=True,
)
def render_scan_info(n_clicks, in_hertz, start_wnum, end_wnum, no_of_steps, time_per_scan, no_of_passes):
    scan_range = end_wnum - start_wnum
    wnum_per_scan = scan_range / no_of_steps
    wnum_to_freq = 30

    if in_hertz:
        mode = "Frequency"
        unit1, unit2 = "GHz", "MHz"
        start_wnum_display = round(start_wnum * wnum_to_freq, 2)
        end_wnum_display = round(end_wnum * wnum_to_freq, 2)
        scan_range_display = round(scan_range * wnum_to_freq * 1000, 7)
        wnum_per_scan_display = round(wnum_per_scan * wnum_to_freq * 1000, 7)
    else:
        mode = "Wavenumber"
        unit1, unit2 = "/cm", "/cm"
        start_wnum_display, end_wnum_display = start_wnum, end_wnum
        scan_range_display = scan_range
        wnum_per_scan_display = round(wnum_per_scan, 5)

    info = [
        f"Start Point({unit1}): {start_wnum_display}",
        f"End Point({unit1}): {end_wnum_display}",
        f"Total Scan Range({unit2}): {scan_range_display}",
        f"Number of Steps: {no_of_steps}",
        f"Time Per Scan(s): {time_per_scan}",
        f"{mode} Per Scan({unit2}): {wnum_per_scan_display}",
        f"Number of Passes: {no_of_passes}"
    ]

    return html.Div([html.P(info_item) for info_item in info], style=text_style['scan_info'])

@app.callback(
    Output('etalon_lock_icon', 'className'),
    Input('etalon_lock_button', 'n_clicks'),
    prevent_initial_call=True,
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
        Output('cavity_lock_icon', 'className'),
        Input('cavity_lock_button', 'n_clicks'),
        prevent_initial_call=True,
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

@app.callback(
        Output('freq_unlock_button', 'disabled'),
        Output('wavelength_locker_status', 'children'),
        Output('wavelength_locker_status', 'style'),
        Input('freq_lock_button', 'n_clicks'),
        Input('freq_unlock_button', 'n_clicks'),
        State('t_wnum', 'value'),
        State('wnum_display', 'children'),
        prevent_initial_call=True,
)
def freq_lock(lock_n_clicks, unlock_n_clicks, t_wnum, c_wnum):
    """Lock in the wavelength of the laser to the number in the target wavenumber widget, if both locks are on"""
    button_id = ctx.triggered_id 
    t_wnum = float(t_wnum)
    c_wnum = float(c_wnum)

    if button_id == 'freq_lock_button':
        if abs(t_wnum - c_wnum) >= 0.1:
            raise_toast('WARNING', 'You are trying to tune cavity for more than 0.1 cm^-1', 'danger')
            return no_update, no_update, no_update
        else:
            # if get_cavity_lock_status() and get_etalon_lock_status():
            #     control_loop.lock(t_wnum)
            #     print('Wavelength locked')
            #     # state["centroid_wnum_default"] = state.t_wnum
            #     #Flag
            #     raise_toast("Notification", "Wavelength locked!", 'success')
            #     return False, "*_Wavelength lock in progress!_*", {'color': colors['status_warning'], 'font-weight': 'bolder'}
            if state['cavity_lock'] and state['etalon_lock']:
                # state["centroid_wnum_default"] = state.t_wnum
                #Flag
                raise_toast("Status Update", "Wavelength locked!", 'success')
                return False, "*_Wavelength lock in progress!_*", {'color': colors['status_warning'], 'font-weight': 'bolder'}
            else:
                control_loop.unlock()
                raise_toast("WARNING", "Something is not locked", 'warninng')
                return no_update, no_update, no_update
    if button_id == 'freq_unlock_button':
        # control_loop.unlock()
        raise_toast("Status Update", "Wavelength unlocked!", "success")
        return True, "*_Wavelength Not Locked_*", {'color': colors['status_inactive'], 'font-weight': 'bolder'}

@app.callback(
        Output('kp', 'disabled'),
        Output('kp', 'value'),
        Input('kp_enable', 'value'),)
def enable_p(kp_enable):
    """Enable or disable the proportional gain"""
    if kp_enable:
        return False, no_update
    else:
        return True, 0.0

@app.callback(
    Output('ki', 'disabled'),
    Output('ki', 'value'),
    Input('ki_enable', 'value'))
def enable_i(ki_enable):
    """Enable or disable the integral gain"""
    if ki_enable:
        return False, no_update
    else:
        return True, 0.0

@app.callback(
    Output('kd', 'disabled'),
    Output('kd', 'value'),
    Input('kd_enable', 'value'))
def enable_d(kd_enable):
    """Enable or disable the derivative gain"""
    if kd_enable:
        return False, no_update
    else:
        return True, 0.0

@app.callback(
    Input('pid_update_button', 'n_clicks'),
    State('kp_enable', 'value'),
    State('ki_enable', 'value'),
    State('kd_enable', 'value'),
    State('kp', 'value'),
    State('ki', 'value'),
    State('kd', 'value'),
    prevent_initial_call=True,)
def pid_update(n_clicks, kp_enable, ki_enable, kd_enable, kp, ki, kd):
    """Update the PID controller gains"""
    if kp_enable:
        print('Proportional gain enabled')
        # control_loop.p_update(kp)
    if ki_enable:
        print('Integral gain enabled')
        # control_loop.i_update(ki)
    if kd_enable:
        print('Derivative gain enabled')
        # control_loop.d_update(kd)
    print(f'PID update button clicked with {kp}, {ki}, {kd}')


@app.callback(
        Output('update_time_per_step', 'disabled'),
        Output('start_scan', 'disabled'),
        Output('stop_scan', 'disabled'),
        Output('scan_status', 'children'),
        Output('scan_status', 'style'),
        Input('start_scan', 'n_clicks'),
        Input('stop_scan', 'n_clicks'),
        State('start_wnum', 'value'),
        State('end_wnum', 'value'),
        State('no_of_steps', 'value'),
        State('wnum_display', 'children'),
        prevent_initial_call=True,
)
def scan(start_n_clicks, end_n_clicks, start_wnum, end_wnum, no_of_steps, c_wnum):
    button_id = ctx.triggered_id
    if button_id =='start_scan':
        update1, update2, update3, update4, update5 = start_scan(start_wnum, end_wnum, no_of_steps, c_wnum)
        return update1, update2, update3, update4, update5
    if button_id =='stop_scan':
        update1, update2, update3, update4, update5 = stop_scan()
        return update1, update2, update3, update4, update5

def start_scan(start_wnum, end_wnum, no_of_steps, c_wnum):
    """Start scanning based on numbers in the widgets if laser frequency is not locked"""
    start_wnum, end_wnum, no_of_steps, c_wnum = float(start_wnum), float(end_wnum), int(no_of_steps), float(c_wnum)
    wnum_per_scan = (end_wnum - start_wnum) / no_of_steps
    #freq_lock_running = control_loop.state
    freq_lock_running = state['state']

    if wnum_per_scan >= 0.1:
        raise_toast('WARNING', 'You are trying to start a scan with one step larger than 0.1 cm^-1', 'danger')
        return no_update, no_update, no_update, no_update, no_update
    if abs(start_wnum - c_wnum) >= 0.1:
        raise_toast('WARNING', 'The start wavenumber must be smaller than 0.1 cm^-1 away from current wavenumber', 'danger')
        return no_update, no_update, no_update, no_update, no_update
    else:               
        if freq_lock_running != 1:
            #control_loop.start_scan(state.start_wnum, state.end_wnum, state.no_of_steps, state.time_per_scan, state.no_of_passes)
            #state.scan = 1
            raise_toast("Status Update", "Scan Started!", 'success')
            scan_text = "_*Scan in Progress !*_"
            scan_text_style={'color': colors['status_warning'], 'font-weight': 'bold', 'font-size': '18px',}
            return False, True, False, scan_text, scan_text_style
        else:
            print('else 2')
            raise_toast('WARNING', 'Unlock the wavelength first before starting a scan!', 'danger')
            return no_update, no_update, no_update, no_update, no_update

def stop_scan():
    """Stop the current scan"""
    #control_loop.stop_scan()
    # state.scan = 0
    scan_text = "_*Scan is Forcibly Stopped !*_"
    scan_text_style={'color': colors['status_warning'], 'font-weight': 'bold', 'font-size': '18px',}
    raise_toast('WARNING', 'Scan stopped!', 'danger')
    return True, False, True, scan_text, scan_text_style

@app.callback(
    Output('dir_status', 'children'),
    Output('dir_status', 'style'),
    Output('memory', 'data'),
    Input('dir_select_button', 'n_clicks'),
    prevent_initial_call=True,
)
def dir_select(n_clicks):
    """Open a directory picker using wx"""
    directory = open_directory_dialog()
    if directory:
        exist_style = {'color': colors['value'], 'font-weight': 'bolder',}
        dir_on_memory = {'dir_to_save': directory}
        dir_on_memory_json = json.dumps(dir_on_memory)
        return f"Selected directory: _{directory}_", exist_style, dir_on_memory_json
    else:
        empty_style = {'color': colors['status_warning'], 'font-weight': 'bolder',}
        return "_No directory selected._]", empty_style, no_update

def open_directory_dialog():
    """Create a directory picker using wx"""
    app = wx.App(False)
    dialog = wx.DirDialog(None, "Choose a directory", style=wx.DD_DEFAULT_STYLE)
    if dialog.ShowModal() == wx.ID_OK:
        path = dialog.GetPath()
    else:
        path = None
    dialog.Destroy()
    return path

@app.callback(
    Output('dir_status', 'children'),
    Output('dir_status', 'style'),
    Input('save_button', 'n_clicks'),
    Input('stop_save_button', 'children'),
    State('file_name', 'value'),
    State('memory', 'data'),
    prevent_initial_call=True,)
def save_data(save_n_clicks, stop_save_n_clicks, file_name, memory_json):
    stored_data = json.loads(memory_json)
    directory = stored_data.get('dir_to_save')
    button_id = ctx.triggered_id
    
    if button_id =='save_button':
        if directory and file_name:
            success_msg = f"_Data automatically being saved to {directory}_"
            success_style = {'color': colors['success'], 'font-weight': 'bolder',}
            return success_msg, success_style
        else: 
            fail_msg = "_No filename/directory specified._"
            fail_style = {'color': colors['status_warning'], 'font-weight': 'bolder',}
            return fail_msg, fail_style
    if button_id =='stop_save_button':
        stopped_msg = f"_Data stopped saving to {directory}_"
        stopped_style = {'color': colors['label'], 'font-weight': 'bolder',}
        # state.dialog_dir = None
        return stopped_msg, stopped_style

@app.callback(
        Input('update_time_per_step', 'n_clicks'),
        State('time_per_scan', 'value'),
        prevent_initial_call=True,)
def update_time_per_step(n_clicks, new_time_per_scan):
    """Update time per scan based on number in the widget"""
    raise_toast("Status Update", "PID Parameters Updated!", 'success')
    #control_loop.scan_update(new_time_per_scan)

# @app.callback(
#     Output('scan_progress', 'value'),
#     Output('scan_progress', 'label'),
#     Output('scan_etc', 'children'),
#     Input('slow-interval', 'n_intervals'),
#     State('stop_scan', 'disabled'),
#     prevent_initial_call=True)
# def update_scan_progress(n_intervals, stop_scan_disabled):
#     """Updates the scan progress bar and status"""
#     if stop_scan_disabled:
#         raise PreventUpdate
#     else:
#         progress = control_loop.scan_progress
#         total_time = control_loop.total_time
#         scan_state = control_loop.scan
#         if scan_state == 1:
#             progress_value, progress_text, etc_text = calculate_scan_progress(progress, total_time)
#             return progress_value, progress_text, etc_text
#         else:
#             # If scan is complete, end the tweaking thread and reset the progress bar
#             #control_loop.stop_tweaking()
#             state.scan_status = ":green[_Scan Finished_]"
#             status_text = "_*Scan is Finished !*_"
#             scan_text_style = {'color': colors['success'], 'font-weight': 'bold', 'font-size': '18px',}
#             etc_text = "*_Estimated Time of Completion: 0 sec left_*"
#             # state.scan = 0
#             raise_toast('Status Update', 'Scan is Finished!', 'success')
#             set_props('update_time_per_step', {'disabled': True})
#             set_props('start_scan', {'disabled': False})
#             set_props('stop_scan', {'disabled': True})
#             set_props('scan_status', {'children': status_text,'style': scan_text_style})
#             return 100, "Scan Completed", etc_text
        
# @app.callback(
    
#     Input('slow-interval', 'n_intervals'))
# def lock_sanity_check(n_intervals):
#     if get_etalon_lock_status():
#         return 

# @app.callback(
#     Output('wnum_display', 'children'),
#     Input('fast-interval', 'n_intervals'))
# def update_current_wnum(n_intervals):
#     """Updates the current wavenumber continuously in the while loop"""
#     try:
#         control_loop.update()
#         c_wnum = get_cwnum()
#         c_wnum = str(c_wnum)
#     except Exception as e:
#         error(e, 'Error in getting current wavenumber', 'warning')

#     return c_wnum

# @app.callback(
#     Output('wavenumber_vs_time', 'figure'),
#     Input('fast-interval', 'n_intervals'))
# def update_plot(n_intervals):
#     """Updates the current wavenumber and plot continuously in the while loop
    
#     Args:
#         plot(placeholder): Placeholder for the plot
#         dataf_space(placeholder: Placeholder for the current wavenumber)
#     """
#     try:
#         xtoPlot, ytoPlot = control_loop.get_df_to_plot()
#         if len(xtoPlot) != len(ytoPlot):
#             error(e, 'The length of time series is different from that of wavenumber', 'warning')
#             return no_update, no_update
#     except Exception as e:
#         error(e, 'Error in getting plot data', 'warning')
#     # Time series plot
#     if xtoPlot and ytoPlot:
#         if len(xtoPlot) < 2:
#             fig = go.Figure(data=go.Scatter(x=xtoPlot, y=ytoPlot, mode='lines+markers', marker=dict(size = 8, color='rgba(255,77,1, 1)')), layout=go.Layout(
#                 xaxis=dict(title="Time(s)"), yaxis=dict(title="Wavenumber (cm^-1)", exponentformat="none"), uirevision=True, paper_bgcolor=colors['main_bg'], plot_bgcolor=colors['sidebar_bg'],  
#                 ))
#             fig.update_xaxes(showgrid=True, gridwidth=1, griddash='dash', minor_griddash="dot", gridcolor='Blue')
#             return fig
#         else:
#             patched_fig = Patch()
#             patched_fig["data"][0]["x"] = xtoPlot
#             patched_fig["data"][0]["y"] = ytoPlot
#             return patched_fig
#         # if state.freq_lock_clicked or state.scan_button:
#         #     y_ref = control_loop.target
#         #     y_lower = y_ref - 0.00002
#         #     y_upper = y_ref + 0.00002
#         #     fig.add_hrect(y0=y_lower, y1=y_upper, line_width=0, fillcolor="LightPink", opacity=0.5)
#     # dataf_space.metric(label="Current Wavenumber", value=state.c_wnum)
#     else: return no_update

def main():
    try:
        app.run(debug=True, dev_tools_hot_reload=False)
    except KeyboardInterrupt:
        control_loop.stop()
        print(1)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=2355)
