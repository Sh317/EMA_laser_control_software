import streamlit as st
import sys
import os
import wx
import time
import traceback
import numpy as np
import plotly
import plotly.graph_objects as go
import cufflinks as cf
import pandas as pd

sys.path.append('.\\src')
from control.st_laser_control import LaserControl

# Streamlit page configuration
st.set_page_config(
    page_title="Laser Control System",
    page_icon=":mirror:",
    layout="wide",
)

st.header("Laser Control System")
sidebar = st.sidebar

# Select which laser to control
laser_options = ["Laser 1", "Laser 2", "Laser 3", "Laser 4"]
selected_laser = sidebar.selectbox("Select Laser", laser_options, index=0)
tag = f"wavenumber_{selected_laser.split(' ')[1]}"

state = st.session_state

# Initialize session state
def initialize_state(key, default_value):
    """Initialize the value for keys in the streamlit session state
    
    Args:
        key(string): The key that needs to be initialized
        default_value(any): The value to be stored in the session state
    """
    if key not in state:
        state[key] = default_value

def initialize_lock(key, condition):
    """Initialize the icon for locks
    
    Args:
        key(string): Lock to be initialized
        condition(bool): Boolean value to be passed based on current lock status
    """
    if key not in st.session_state:
        get_lock_icon(key, condition)

initialize_state("netcon_tries", 0)
initialize_state("freq_lock_clicked", False)
initialize_state('kp_enable', False)
initialize_state('ki_enable', False)
initialize_state('kd_enable', True)
initialize_state("scan", 0)
initialize_state("scan_button", False)
initialize_state("scan_status", ":green[_Ready for Scan_]")
initialize_state("dialog_dir", None)
initialize_state("backup_enable", False)
initialize_state("backup_name", None)
initialize_state("backup_dir", None)
initialize_state("df_toSave", None)
initialize_state("max_points", 100)  # Limit to last 100 points for plotting

def error_page(description, error):
    """Error page UI when error occurs
    
    Args:
        description(string): The description of the error
        error: Error that occured
        
    """
    st.error(description, icon="🚨")
    e1, e2 = st.columns(2)
    with e1.expander("View Error Details"):
        st.write(f"Error: {str(error)} \n {traceback.format_exc()}")
    if e2.button("Try Again!", type="primary"):
        st.rerun()

def ins_laser(laser_tag):
    """Instantiate the laser control class with selected laser tag
    
    Arg:
        laser_tag(string): Specify which laser to talk to
    """
    return LaserControl("192.168.1.222", 39933, f"LaserLab:{laser_tag}", verbose=True)

def patient_netconnect(tryouts=10):
    """Try to instantiate the laser class if this is the first call, otherwise inherit the properties.
    
    Arg:
        tryouts(int): The number of tries to initialize the laser setting. Default is 10 times
    """
    global control_loop
    while state.netcon_tries <= tryouts:
        try:
            if "control_loop" not in state:
                control_loop = ins_laser(tag)
            else:
                control_loop = state.control_loop
            break
        except Exception as e:
            state.netcon_tries += 1
            print(f"Unable to initialize the laser control due to error: {e} \n {traceback.format_exc()}")
            st.rerun()
    if state.netcon_tries > tryouts:
        error_page(f"Unable to initialize the laser control after {tryouts} tries.", ConnectionError)
        raise ConnectionError

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

def get_lock_icon(key, condition):
    """Sets the lock icon in the session state based on the condition
    
    Args:
        key(string): The key in the session state for lock status
        condition(bool): The boolean value based on the lock status
    """
    if condition:
        st.session_state[key] = "🔐"
    else:
        st.session_state[key] = "🔓"   

def lock_etalon():
    """Lock etalon if it's unlocked and unlock otherwise"""
    if get_etalon_lock_status():
        control_loop.unlock_etalon()
        state["etalon_lock"] = "🔓"
    else:
        control_loop.lock_etalon()
        state["etalon_lock"] = "🔐"
    control_loop.update_etalon_lock_status()

def lock_cavity():
    """Lock cavity if it's unlocked and unlock otherwise"""
    if get_cavity_lock_status():
        control_loop.unlock_reference_cavity()
        state["cavity_lock"] = "🔓"
    else:
        control_loop.lock_reference_cavity()
        state["cavity_lock"] = "🔐"
    control_loop.update_ref_cav_lock_status()

def tune_etalon():
    """Call tune etalon function to tune the etalon to the value specified in the etalon tuner"""
    control_loop.tune_etalon(state.etalon_tuner)

def tune_ref_cav():
    """Call tune reference cavity function to tune the reference cavity to the value specified in the cavity tuner"""    
    control_loop.tune_reference_cavity(state.cavity_tuner)

def freq_lock():
    """Lock in the wavelength of the laser to the number in the target wavenumber widget, if both locks are on"""
    if control_loop.reference_cavity_lock_status == "on" and control_loop.etalon_lock_status == "on":
        control_loop.lock(state.t_wnum)
        state["freq_lock_clicked"] = True
        state["centroid_wnum_default"] = state.t_wnum
        st.toast("✅ Wavelength locked!")
    else:
        control_loop.unlock()
        st.toast("❗ Something is not locked ❗")

def freq_unlock():
    """Unlock the wavelength of the laser"""
    control_loop.unlock()
    st.toast("✅ Wavelength unlocked!")
    state["freq_lock_clicked"] = False

def pid_update():
    """Update pid value to the number in the slider if enabled, otherwise set to 0"""
    control_loop.p_update(1.0 if state.kp_enable else state.kp)
    control_loop.i_update(0.0 if state.ki_enable else state.ki)
    control_loop.d_update(0.0 if state.kd_enable else state.kd)

def start_scan():
    """Start scanning based on numbers in the widgets if laser frequency is not locked"""
    if not state.freq_lock_clicked:
        control_loop.start_scan(state.start_wnum, state.end_wnum, state.no_of_steps, state.time_per_scan, state.no_of_passes)
        state.scan_button = True
        state.scan_status = ":red[_Scan in Progress_]"
        state.scan = 1
        st.toast("👀 Scan started!")
    else:
        st.toast("👿 Unlock the wavelength first before starting a scan!")

def stop_scan():
    """Stop the current scan"""
    control_loop.stop_scan()
    state.scan_button = False
    state.scan_status = ":red[_Scan is Forcibly Stopped_]"
    state.scan = 0
    st.toast("👀 Scan stopped!")

def end_scan(placeholder):
    """Ends the scan and redraw the UI widgets"""
    control_loop.stop_tweaking()
    state.scan_button = False
    state.scan_status = ":green[_Scan Finished_]"
    state.scan = 0
    draw_scanning(placeholder, "scan_complete")
    st.toast("Scan Completed!")

def scan_update():
    """Update time per scan based on number in the widget"""
    control_loop.scan_update(state.time_per_scan)

def clear_plot():
    """Clear plot"""
    control_loop.clear_plot()

@st.cache_data
def get_rate():
    """Get reading rate"""
    return control_loop.rate

def get_cwnum():
    """Get current wavenumber"""
    return control_loop.get_current_wnum()

def get_pid():
    """Get pid coefficients"""
    return control_loop.pid.kp, control_loop.pid.ki, control_loop.pid.kd

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

def start_saving(name, path):
    """Start saving data on teh background
    
    Args:
        name(str): Filename
        path(str): Location to save file to
    """
    if state.dialog_dir:
        filename = f"{name}.csv"
        filepath = os.path.join(path, filename)
        control_loop.start_backup_saving(filepath)
        state.backup_enable = True

def stop_saving():
    """Stop saving data on the background"""
    control_loop.stop_backup_saving()
    state.backup_enable = False

def get_reading_thread_status():
    """Get status of the reading thread
    
    Return:
        str: The status of the reading thread
    """
    status = control_loop.reader.reading_thread
    if status is None:
        return ":blue[Reading thread is not on]"
    else: return ":red[Reading thread is on duty]"

def get_saving_status():
    """Return corresponding texts based on whether data are being saved to the disk
    
    Return:
        str: The status of data saving"""
    directory = control_loop.reader.saving_dir
    if directory is None:
        return ":blue[Data is not being saved]"
    else: return f":red[Data is being saved to {directory}]"

def get_tweaking_thread_status():
    """Get the status of the tweaking thread
    
    Returns:
        str: The status of the tweaking thread
    """
    status = control_loop.tweaking_thread
    if status is None:
        return ":blue[Tweaking thread is not on]"
    else: return f":red[Tweaking thread is on duty]"

def stop_reading_thread():
    """Catch the reading thread"""
    control_loop.stop_reading

def stop_tweaking_thread():
    """Catch the tweaking thread"""
    control_loop.stop_tweaking

def update_values():
    """Trigger rerun to update default values in the widgets"""
    state.c_wnum = get_cwnum()
    state.cavity_tuner_value = round(float(control_loop.get_ref_cav_tuner()), 5)
    state.etalon_tuner_value = round(float(control_loop.get_etalon_tuner()), 5)
    st.rerun()
    
def calculate_total_points(time_ps, rate, no_steps):
    total_points = float(time_ps * no_steps)
    total_time = time_ps * no_steps
    return total_points, total_time

def calculate_progress(progress, total_time):
    percent = round(progress / total_time, 4)
    if percent >= 1:
        percent = 1.
    etc = round((1 - percent) * total_time, 1)
    current_pass = control_loop.current_pass
    current_pass += 1
    progress_text = f"*Pass {current_pass}*: {percent:.2%} % of scan have completed. :blue[_Estimated Time of Completion: {etc} seconds left_]"
    return percent, progress_text

def draw_progress_bar(total_time, progress_bar, scan_placeholder):
    progress = control_loop.scan_progress
    scan = control_loop.scan
    if scan == 1:
        percent, progress_text = calculate_progress(progress, total_time)
        progress_bar.progress(percent, text=progress_text)
    else:
        print("scan stopped")
        end_scan(scan_placeholder)
        progress_bar.progress(1., text="Scan Completed!")

def control_loop_update():
    state.control_loop = control_loop
    control_loop.update()

def loop(plot, dataf_space):
    """Loop function that updates the current wavenumber and plot continuously in the while loop
    
    Args:
        plot(placeholder): Placeholder for the plot
        dataf_space(placeholder: Placeholder for the current wavenumber)
    """
    try:
        xtoPlot, ytoPlot = control_loop.get_df_to_plot()
        control_loop_update()
        c_wnum = get_cwnum()
    except Exception as e:
        error_page("Unable to update laser information.", e)
    # Time series plot
    if xtoPlot and ytoPlot:
        fig = go.Figure(data=go.Scatter(x=xtoPlot, y=ytoPlot, mode='lines+markers', marker=dict(size = 8, color='rgba(255,77,1, 1)')), layout=go.Layout(
            xaxis=dict(title="Time(s)"), yaxis=dict(title="Wavenumber (cm^-1)", exponentformat="none")
            ))
        fig.update_xaxes(showgrid=True, gridwidth=1, griddash='dash', minor_griddash="dot", gridcolor='Blue')
        #fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightPink')
        if state.freq_lock_clicked or state.scan_button:
            y_ref = control_loop.target
            y_lower = y_ref - 0.00002
            y_upper = y_ref + 0.00002
            fig.add_hrect(y0=y_lower, y1=y_upper, line_width=0, fillcolor="LightPink", opacity=0.5)
        #fig = dataf.iplot(kind="scatter", title="Wavenumber VS Time", xTitle="Time(s)", yTitle="Wavenumber (cm^-1)", asFigure=True, mode="lines+markers", size=8, colors=["pink"])
        # fig.update_xaxes(exponentformat="none")
        # fig.update_yaxes(exponentformat="none")
        plot.plotly_chart(fig, theme='streamlit', use_container_width=True)
    dataf_space.metric(label="Current Wavenumber", value=c_wnum)



def scan_settings():
    """Draw UI components for scan settings and expander to show info about scanning"""
    initialize_state('centroid_wnum_default', get_cwnum())
    st.header("Scan Settings")
    c1, c2 = st.columns(2, vertical_alignment='top')
    start_wnum = c1.number_input("Start Wavenumber (cm^-1)", value=state.centroid_wnum_default, step=0.00001, format="%0.5f", key="start_wnum")
    end_wnum = c2.number_input("End Wavenumber (cm^-1)", value=state.centroid_wnum_default, step=0.00001, format="%0.5f", key="end_wnum")
    no_of_steps = c1.number_input("No. of Steps", value=5, max_value=500, key="no_of_steps")
    time_per_scan = c2.number_input("Time per Step (sec)", value=2.0, step=1., key="time_per_scan")
    no_of_passes = c1.number_input("No. of Passes", value=1, max_value=10, key="no_of_passes")
    scan_range = end_wnum - start_wnum
    wnum_per_scan = scan_range / no_of_steps
    wnum_to_freq = 30
    no_of_steps_display, time_per_scan_display = no_of_steps, time_per_scan
    exscander = st.expander("Scan Info")
    with exscander:
        col1, col2 = st.columns(2)
        conversion_checkbox = col1.checkbox("In Hertz? (Wavenumber in default)", value=True)
        col2.markdown(":red[_Please review everything before scanning_]")
        if conversion_checkbox: 
            mode = "Frequency"
            unit1 = "GHz"
            unit2 = "MHz"
            start_wnum_display, end_wnum_display, scan_range_display, wnum_per_scan = round(start_wnum * wnum_to_freq,2), round(end_wnum * wnum_to_freq,2), round(scan_range * wnum_to_freq * 1000, 7), round(wnum_per_scan * wnum_to_freq *1000, 7)
        else:
            mode = "Wavenumber"
            unit1, unit2 = "/cm", "/cm"
            start_wnum_display, end_wnum_display, scan_range_display, no_of_steps_display = start_wnum, end_wnum, scan_range, no_of_steps
        st.markdown(f"Start Point({unit1}): :orange-background[{start_wnum_display}]")
        st.markdown(f"End Point({unit1}): :orange-background[{end_wnum_display}]")
        st.markdown(f"Total Scan Range({unit2}): :orange-background[{scan_range_display}]")
        st.markdown(f"Number of Steps: :orange-background[{no_of_steps_display}]")
        st.markdown(f"Time Per Scan(s): :orange-background[{time_per_scan_display}]")
        st.markdown(f"{mode} Per Scan({unit2}): :orange-background[{wnum_per_scan}]")
        st.markdown(f"Number of passes: :orange-background[{no_of_passes}]")


def draw_scanning(placeholder, key):
    """Draws the UI components for scanning buttons and widgets
    
    Args:
        placeholder(st.empty): placeholder for scan buttons and status message
        key(str): Suffix for widgets' keys
    """
    button1, button2 = placeholder.columns([1, 1])
    button1.button("Start Scan", on_click=start_scan, disabled=state.scan_button, key=f"start_{key}")
    button2.button("Stop Scan", on_click=stop_scan, type="primary", disabled=not state.scan_button, key=f"stop_{key}")
    button1.markdown(state.scan_status)
    button2.button("Update Time per Step", on_click=scan_update, disabled=not state.scan_button, key=f"update_tps_{key}")

def main():
    """Main function that draws UI"""
    patient_netconnect()
    state.netcon_tries = 0
    sleep_time = get_rate()

    tab1, tab2, tab3, tab4 = sidebar.tabs(["Control", "Scan", "Save to", "Thread(s) Info"])

    etalon_lock_status = get_etalon_lock_status()
    cavity_lock_status = get_cavity_lock_status()
    initialize_lock("etalon_lock", etalon_lock_status)
    initialize_lock("cavity_lock", cavity_lock_status)
    initialize_state('c_wnum', get_cwnum())
    initialize_state("cavity_tuner_value", round(float(control_loop.get_ref_cav_tuner()), 5))
    initialize_state("etalon_tuner_value", round(float(control_loop.get_etalon_tuner()), 5))

    kp, ki, kd = get_pid()
    initialize_state("kp_default", kp)
    initialize_state("ki_default", ki)
    initialize_state("kd_default", kd)

    with tab1:
        st.header("SolsTis Control")
        l1, l2, l3 = st.columns([1, 1, 3], vertical_alignment="center")
        l1.write("**Etalon**")
        l2.button(label=str(state.etalon_lock), on_click=lock_etalon, key="etalon_lock_button")
        l3.number_input("a", key="etalon_tuner", label_visibility="collapsed", value=state.etalon_tuner_value, format="%0.5f", on_change=tune_etalon, disabled=etalon_lock_status)

        ll1, ll2, ll3 = st.columns([1, 1, 3], vertical_alignment="center")
        ll1.write("**Cavity**")
        ll2.button(label=str(state.cavity_lock), on_click=lock_cavity, key="cavity_lock_button")
        ll3.number_input("a", key="cavity_tuner", label_visibility="collapsed", value=state.cavity_tuner_value, step=0.0001, format="%0.4f", on_change=tune_ref_cav)

        st.header("Wavelength Locker")
        with st.form("Lock Wavenumber", border=False):
            a1, a2 = st.columns([2.7, 1], vertical_alignment="bottom")
            t_wnum = a1.number_input("Target Wavenumber (cm^-1)", value=state.c_wnum, step=0.00001, format="%0.5f", key="t_wnum")
            a2.form_submit_button("Lock", on_click=freq_lock)

        unlock1, unlock2 = st.columns([2.7, 1], vertical_alignment="bottom")
        unlock1.markdown(":blue[_Wavelength Not Locked_]" if not state.freq_lock_clicked else ":red[_Wavelength Lock in Progress_]")
        unlock2.button("Unlock", disabled=not state.freq_lock_clicked, on_click=freq_unlock)

        st.subheader("PID Control")
        word1, word2 = st.columns([3, 1], vertical_alignment="bottom")
        word2.write("Enable")
        pid1, pid2 = st.columns([3, 1], vertical_alignment="top")
        with pid2:
            st.write('<div style="height: 26px;">\n</div>', unsafe_allow_html=True)
            kp_enable = st.checkbox("p", value=not state.kp_enable)
            st.write('<div style="height: 38px;">\n</div>', unsafe_allow_html=True)
            ki_enable = st.checkbox("i", value=not state.ki_enable)
            st.write('<div style="height: 38px;">\n</div>', unsafe_allow_html=True)
            kd_enable = st.checkbox("d", value=not state.kd_enable)

        state.kp_enable = not kp_enable
        state.ki_enable = not ki_enable
        state.kd_enable = not kd_enable

        with pid1.form("PID Control", border=False):
            kp = st.slider("Proportional Gain", min_value=0.0, max_value=100.0, value=state.kp_default, step=0.1, format="%0.2f", key="kp", disabled=state.kp_enable)
            ki = st.slider("Integral Gain", min_value=0.0, max_value=10.0, value=state.ki_default, step=0.1, format="%0.2f", key="ki", disabled=state.ki_enable)
            kd = st.slider("Derivative Gain", min_value=0.0, max_value=10.0, value=state.kd_default, step=0.1, format="%0.2f", key="kd", disabled=state.kd_enable)
            if st.form_submit_button("Update", on_click=pid_update):
                st.toast("PID Control Updated!")

    with tab2:
        scan_settings()
        scan_placeholder = st.empty()
        draw_scanning(scan_placeholder, "create")
        scan_bar = st.progress(0., text="Scan Progress")
    
    with tab3: 
        backup_name = st.text_input("File Name:", placeholder="Enter the file name...")
        #backup_dir = st.text_input("File path:", placeholder="Enter the full path...")
        col1, col2 = st.columns([1.5, 4], vertical_alignment="bottom")
        status_msg = col2.empty()
        stop_button = col2.empty()
        if col1.button("Select Directory"):
            directory = open_directory_dialog()
            if directory:
                status_msg.markdown(f"Selected directory: _{directory}_")
                state.dialog_dir = directory

            else:
                status_msg.markdown(":red[_No directory selected._]")
        if col1.button("Start Saving Data", disabled = state.backup_enable, on_click=start_saving, args=(backup_name, state.dialog_dir,)):
            if state.dialog_dir:
                status_msg.markdown(f":green[_Data automatically being saved to {state.dialog_dir}_]")
            else: status_msg.markdown(f":red[_No filename/directory specified._]")
        if stop_button.button("Stop Saving Data", disabled = not state.backup_enable, on_click=stop_saving):
            status_msg.markdown(f":blue[_Data stopped saving to {state.dialog_dir}_]")
            state.dialog_dir = None

    with tab4:
        reading_status = get_reading_thread_status()
        saving_status  = get_saving_status()
        tweaking_status = get_tweaking_thread_status()
        st.subheader("Reading and Saving Thread")
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        c1.markdown(f"Reading: {reading_status}")
        c2.button("Stop Reading", on_click=stop_reading_thread)
        c11, c12 = st.columns([3, 1], vertical_alignment="bottom")
        c11.markdown(f"Saving: {saving_status}")
        c12.button("Stop Saving", on_click=stop_saving)
        st.markdown("❕:red[Caution: Saving will be stopped when reading thread stopped]")
        st.subheader("Laser Tweaking Thread")
        c21, c22 = st.columns([3, 1], vertical_alignment="bottom")
        c21.markdown(f"Laser Tweaking: {tweaking_status}")
        c22.button("Stop Tweaking", on_click=stop_tweaking_thread)

    plot = st.empty()
    place1, place2, place3, place4, place5, place6 = st.columns([4, 3, 1, 1, 1, 1], vertical_alignment="center")
    dataf_space = place1.empty()
    reading_rate = place2.empty()
    if place3.button("Update Value", help="Trigger rerun to update values in the input"):
        update_values()
    place4.button("Clear Plot", on_click=clear_plot)
    if place5.button("Rerun", type="primary"):
        st.rerun()
    place6.button("Stop Child Thread(s)", on_click=control_loop.stop)

    while True:
        reading_rate.metric(label="Reading Rate (s)", value=sleep_time)
        if state.scan == 1:
            total_time = control_loop.total_time
            draw_progress_bar(total_time, scan_bar, scan_placeholder)
        loop(plot, dataf_space)
        time.sleep(0.1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        control_loop.stop()
