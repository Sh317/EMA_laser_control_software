import streamlit as st
import sys
import os
import time
import traceback
import numpy as np
import plotly
import cufflinks as cf
import pandas as pd
from tkinter import Tk
from tkinter.filedialog import askdirectory

setattr(plotly.offline, "__PLOTLY_OFFLINE_INITIALIZED", True)
sys.path.append('.\\src')
from control.st_laser_control import LaserControl

# Set the cufflinks to offline mode
cf.set_config_file(world_readable=True, theme='white')
cf.go_offline()

# Hide the root Tkinter window
root = Tk()
root.withdraw()

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
    if key not in state:
        state[key] = default_value

initialize_state("netcon_tries", 0)
initialize_state("etalon_lock", "🔓")
initialize_state("cavity_lock", "🔓")
initialize_state("freq_lock_clicked", False)
initialize_state("scan_button", False)
initialize_state("df_toSave", None)
initialize_state("max_points", 100)  # Limit to last 100 points for plotting

def error_page(description, error):
    st.error(description, icon="🚨")
    e1, e2 = st.columns(2)
    with e1.expander("View Error Details"):
        st.write(f"Error: {str(error)} \n {traceback.format_exc()}")
    if e2.button("Try Again!", type="primary"):
        st.experimental_rerun()

def ins_laser(laser_tag):
    return LaserControl("192.168.1.222", 39933, f"LaserLab:{laser_tag}")

def patient_netconnect(tryouts=10):
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
            st.error(f"Unable to initialize the laser control due to error: {e}")
            st.experimental_rerun()
    if state.netcon_tries > tryouts:
        error_page(f"Unable to initialize the laser control after {tryouts} tries.", e)
        raise ConnectionError

def etalon_lock_status():
    e_status = control_loop.etalon_lock_status
    assert isinstance(e_status, str) and e_status in ["on", "off"], f"Invalid etalon lock status: {e_status}"
    return e_status == "on"

def cavity_lock_status():
    c_status = control_loop.reference_cavity_lock_status
    assert isinstance(c_status, str) and c_status in ["on", "off"], f"Invalid cavity lock status: {c_status}"
    return c_status == "on"

def lock_etalon():
    if etalon_lock_status():
        control_loop.unlock_etalon()
        state["etalon_lock"] = "🔓"
    else:
        control_loop.lock_etalon()
        state["etalon_lock"] = "🔐"

def lock_cavity():
    if cavity_lock_status():
        control_loop.unlock_reference_cavity()
        state["cavity_lock"] = "🔓"
    else:
        control_loop.lock_reference_cavity()
        state["cavity_lock"] = "🔐"

def freq_lock():
    if control_loop.reference_cavity_lock_status == "on" and control_loop.etalon_lock_status == "on":
        control_loop.lock(state.t_wnum)
        state["freq_lock_clicked"] = True
        state["centroid_wnum_default"] = state.t_wnum
        st.toast("✅ Wavelength locked!")
    else:
        control_loop.unlock()
        st.toast("❗ Something is not locked ❗")

def freq_unlock():
    control_loop.unlock()
    st.toast("✅ Wavelength unlocked!")
    state["freq_lock_clicked"] = False

def pid_update():
    control_loop.p_update(1.0 if state.kp_enable else state.kp)
    control_loop.i_update(0.0 if state.ki_enable else state.ki)
    control_loop.d_update(0.0 if state.kd_enable else state.kd)

def start_scan():
    if not state.freq_lock_clicked:
        control_loop.start_scan(state.start_wnum, state.end_wnum, state.no_of_steps, state.time_per_scan)
        state.scan_button = True
        st.toast("👀 Scan started!")
    else:
        st.toast("👿 Unlock the wavelength first before starting a scan!")

def stop_scan():
    control_loop.stop_scan()
    state.scan_button = False
    st.toast("👀 Scan stopped!")

def scan_update():
    control_loop.scan_update(state.time_per_scan)

def clear_plot():
    control_loop.clear_plot()

def clear_data():
    control_loop.clear_dataset()

def save_file(data):
    filename = st.text_input("File Name:", placeholder="Enter the file name...")
    folder_selected = askdirectory()
    if folder_selected:
        try:
            name = f"{filename}.csv"
            path = os.path.join(folder_selected, name)
            data.to_csv(path, index=False, mode="x")
            st.success(f"File saved successfully to {path}")
        except Exception as e:
            st.error(f"**Failed to save file due to an error:** {e}")

def calculate_progress(progress, goal):
    percent = progress / goal
    progress_text = f"{percent:.2%} of scan completed"
    return percent, progress_text

def draw_progress_bar(point, total_points, progress_bar):
    percent, progress_text = calculate_progress(point, total_points)
    progress_bar.progress(percent, text=progress_text)

def loop(plot, dataf_space, reading_rate):
    try:
        state.control_loop = control_loop
        control_loop.update()
    except Exception as e:
        error_page("Unable to update laser information.", e)

    # Time series plot
    ts, wn, ts_with_time, wn_with_time = control_loop.xDat, control_loop.yDat, control_loop.xDat_with_time, control_loop.yDat_with_time
    if ts and wn:
        # Only use the last 'max_points' data points for plotting
        ts = ts[-state.max_points:]
        wn = wn[-state.max_points:]
        ts_with_time = ts_with_time[-state.max_points:]
        wn_with_time = wn_with_time[-state.max_points:]

        dataf = pd.DataFrame({"Wavenumber (cm^-1)": wn}, index=ts)
        fig = dataf.iplot(kind="scatter", title="Wavenumber VS Time", xTitle="Time(s)", yTitle="Wavenumber (cm^-1)", asFigure=True, mode="lines+markers", colors=["pink"])
        fig.update_xaxes(exponentformat="none")
        fig.update_yaxes(exponentformat="none")
        plot.plotly_chart(fig)
        dataf_space.metric(label="Current Wavenumber", value=wn[-1])
        state.df_toSave = pd.DataFrame({'Time': ts_with_time, 'Wavenumber': wn_with_time})

    reading_rate.metric(label="Reading Rate (ms)", value=control_loop.rate)
    time.sleep(control_loop.rate * 0.001)

def scan_settings():
    st.header("Scan Settings")
    c1, c2 = st.columns(2, vertical_alignment='bottom')
    state.start_wnum = c1.number_input("Start Wavenumber (cm^-1)", value=state.centroid_wnum_default, step=0.00001, format="%0.5f", key="start_wnum")
    state.end_wnum = c2.number_input("End Wavenumber (cm^-1)", value=state.centroid_wnum_default, step=0.00001, format="%0.5f", key="end_wnum")
    state.no_of_steps = c1.number_input("No. of Steps", value=5, max_value=500, key="no_of_steps")
    state.time_per_scan = c2.number_input("Time per Step (sec)", value=2.0, step=1., key="time_per_scan")
    scan_range = state.end_wnum - state.start_wnum
    wnum_per_scan = scan_range / state.no_of_steps
    wnum_to_freq = 30
    exscander = st.expander("Scan Info")
    with exscander:
        col1, col2 = st.columns(2)
        conversion_checkbox = col1.checkbox("In Hertz? (Wavenumber in default)", value=True)
        col2.markdown(":red[_Please review everything before scanning_]")
        if conversion_checkbox:
            mode = "Frequency"
            unit1 = "GHz"
            unit2 = "MHz"
            start_wnum_display, end_wnum_display, scan_range_display, wnum_per_scan = state.start_wnum * wnum_to_freq, state.end_wnum * wnum_to_freq, round(scan_range * wnum_to_freq * 1000, 7), round(wnum_per_scan * wnum_to_freq *1000, 7)
        else:
            mode = "Wavenumber"
            unit1, unit2 = "/cm", "/cm"
            start_wnum_display, end_wnum_display, scan_range_display, no_of_steps_display = state.start_wnum, state.end_wnum, scan_range, state.no_of_steps
        st.markdown(f"Start Point({unit1}): :orange-background[{start_wnum_display}]")
        st.markdown(f"End Point({unit1}): :orange-background[{end_wnum_display}]")
        st.markdown(f"Total Scan Range({unit2}): :orange-background[{scan_range_display}]")
        st.markdown(f"Number of Steps: :orange-background[{no_of_steps_display}]")
        st.markdown(f"Time Per Scan(s): :orange-background[{state.time_per_scan}]")
        st.markdown(f"{mode} Per Scan({unit2}): :orange-background[{wnum_per_scan}]")

def main():
    patient_netconnect()

    tab1, tab2 = sidebar.tabs(["Control", "Scan"])

    with tab1:
        st.header("SolsTis Control")
        l1, l2, l3 = st.columns([1, 1, 3], vertical_alignment="center")
        l1.write("**Etalon**")
        l2.button(label=str(state["etalon_lock"]), on_click=lock_etalon, key="etalon_lock_button")
        l3.number_input("a", key="etalon_tuner", label_visibility="collapsed", value=round(float(control_loop.etalon_tuner_value), 5), format="%0.5f", disabled=etalon_lock_status())

        ll1, ll2, ll3 = st.columns([1, 1, 3], vertical_alignment="center")
        ll1.write("**Cavity**")
        ll2.button(label=str(state["cavity_lock"]), on_click=lock_cavity, key="cavity_lock_button")
        ll3.number_input("a", key="cavity_tuner", label_visibility="collapsed", value=round(float(control_loop.reference_cavity_tuner_value), 5), format="%0.5f")

        st.header("Wavelength Locker")
        with st.form("Lock Wavenumber", clear_on_submit=True):
            a1, a2 = st.columns([2.7, 1], vertical_alignment="bottom")
            state.t_wnum = a1.number_input("Target Wavenumber (cm^-1)", value=round(float(control_loop.wavenumber.get()), 5), step=0.00001, format="%0.5f", key="t_wnum")
            if a2.form_submit_button("Lock", on_click=freq_lock):
                st.toast("Wavelength Locked!")

        unlock1, unlock2 = st.columns([2.7, 1], vertical_alignment="bottom")
        unlock1.markdown(":red[_Wavelength Not Locked_]" if not state.freq_lock_clicked else ":red[_Wavelength Lock in Progress_]")
        unlock2.button("Unlock", disabled=not state.freq_lock_clicked, on_click=freq_unlock)

        st.subheader("PID Control")
        word1, word2 = st.columns([3, 1], vertical_alignment="bottom")
        word2.write("Enable")
        pid1, pid2 = st.columns([3, 1], vertical_alignment="top")
        kp_enable = pid2.checkbox("p", value=not state.kp_enable)
        ki_enable = pid2.checkbox("i", value=not state.ki_enable)
        kd_enable = pid2.checkbox("d", value=not state.kd_enable)

        state.kp_enable = not kp_enable
        state.ki_enable = not ki_enable
        state.kd_enable = not kd_enable
        with pid1.form("PID Control", clear_on_submit=True):
            state.kp = st.slider("Proportional Gain", min_value=0.0, max_value=50.0, value=50.0, step=0.1, format="%0.2f", key="kp")
            state.ki = st.slider("Integral Gain", min_value=0.0, max_value=10.0, value=0.0, step=0.1, format="%0.2f", key="ki", disabled=state.ki_enable)
            state.kd = st.slider("Derivative Gain", min_value=0.0, max_value=10.0, value=0.0, step=0.1, format="%0.2f", key="kd", disabled=state.kd_enable)
            if st.form_submit_button("Update", on_click=pid_update):
                st.toast("PID Control Updated!")

    with tab2:
        scan_settings()
        button1, button2, button3 = st.columns([1, 1, 3])
        button1.button("Start Scan", on_click=start_scan, disabled=state.scan_button)
        button2.button("Stop Scan", on_click=stop_scan, disabled=not state.scan_button)
        button3.button("Update Time per Step", on_click=scan_update, disabled=not state.scan_button)
        scan_bar = st.progress(0, text="Scan Progress")

    plot = st.empty()
    place1, place2, place3, place4, place5 = st.columns([4, 3, 1, 1, 1], vertical_alignment="center")
    dataf_space = place1.empty()
    reading_rate = place2.empty()
    if place3.button("Save"):
        save_file(state.df_toSave)
    if place4.button("Clear Plot"):
        clear_plot()
    if place5.button("Rerun", type="primary"):
        st.experimental_rerun()

    while True:
        loop(plot, dataf_space, reading_rate)

if __name__ == "__main__":
    main()
