import streamlit as st
import sys
import os
import time
import traceback
import numpy as np
import plotly
import cufflinks as cf
import pandas as pd

setattr(plotly.offline, "__PLOTLY_OFFLINE_INITIALIZED", True)
sys.path.append('.\\src')
from control.st_laser_control import LaserControl


cf.set_config_file(world_readable=True,theme='white')
cf.go_offline()


st.set_page_config(
    page_title="Laser Control System",
    page_icon=":mirror:",
    layout="wide",
)

st.header("Laser Control System")

sidebar = st.sidebar
# select which laser to control
i = sidebar.selectbox("Select Laser", ["Laser 1", "Laser 2", "Laser 3", "Laser 4"], index=0)
tag = f"wavenumber_{i.split(" ")[1]}"
control_loop = False
state = st.session_state
def initialize_state(key, default_value):
    if key not in st.session_state:
        state[key] = default_value

 
def error_page(description, error):
    st.error(description, icon="🚨")
    e1, e2 = st.columns(2)
    with e1.popover(label="View Error Details"):
        st.write(f"Error: {str(error)} \n {traceback.format_exc()}")
    rerun = e2.button("Try Again!", type="primary")
    if rerun:
        st.rerun()

def ins_laser(laser_tag):
    return LaserControl("192.168.1.222", 39933, f"LaserLab:{laser_tag}")

def patient_netconnect(tryouts = 10):
    if "netcon_tries" not in state:
        state.netcon_tries = 0
    global control_loop
    while state.netcon_tries <= tryouts:
        try:
            if "control_loop" not in state:
                control_loop = ins_laser(tag)
            else:
                control_loop = state.control_loop
            # print("class instantiated again")
            break
        except Exception as e:
            state.netcon_tries += 1
            print(f"Unable to initialize the laser control due to error: {e} \n {traceback.format_exc()}")
            st.rerun()
    if state.netcon_tries > tryouts:
        error_page(description=f"Unable to initialize the laser control after {tryouts} tries.", error=e)
        raise ConnectionError

def main(): 
    #1/0
    try:
        patient_netconnect()
        control_loop.update()
        #control_loop.state = state.laser_state
    except Exception as e:
        error_page(description="Unable to communicate with the laser control module.", error=e)

    #print("It has proceeded to the main part now")
    #sidebar
    tab1, tab2 = sidebar.tabs(["Control", "Scan"])

    #tab1 - Control
    tab1.header("SolsTis Control")
    l1, l2, l3 = tab1.columns([1, 1, 3], vertical_alignment="center")


    
    #locks
    l1.write("**Etalon**")
    etalon_lock = l2.empty()
    etalon_tuner = l3.empty()

    ll1, ll2, ll3 = tab1.columns([1, 1, 3], vertical_alignment="center")
    ll1.write("**Cavity**")
    cavity_lock = ll2.empty()
    cavity_tuner = ll3.empty()

    def etalon_lock_status():
        e_status = control_loop.etalon_lock_status
        assert isinstance(e_status, str) and e_status in ["on", "off"], f"Invalid etalon lock status: {e_status}"
        return True if  e_status == "on" else False
    
    etalon_lock_status = etalon_lock_status()
    if "etalon_lock" not in st.session_state:
        if etalon_lock_status:
            st.session_state["etalon_lock"] = "🔐"
        else:
            st.session_state["etalon_lock"] = "🔓"

    
    def lock_etalon():
        if etalon_lock_status:
            control_loop.unlock_etalon()
            st.session_state["etalon_lock"] = "🔓"
        else:
            control_loop.lock_etalon()
            st.session_state["etalon_lock"] = "🔐"


    etalon_lock.button(label=str(st.session_state["etalon_lock"]), on_click=lock_etalon, key="etalon_lock_button")
    
    def cavity_lock_status():
        c_status = control_loop.reference_cavity_lock_status
        assert isinstance(c_status, str) and c_status in ["on", "off"], f"Invalid cavity lock status: {c_status}"
        return True if  c_status == "on" else False
    
    cavity_lock_status = cavity_lock_status()
    if "cavity_lock" not in st.session_state:
        if cavity_lock_status:
            st.session_state["cavity_lock"] = "🔐"
        else:
            st.session_state["cavity_lock"] = "🔓"

    def lock_cavity():
        if cavity_lock_status:
            control_loop.unlock_reference_cavity()
            st.session_state["cavity_lock"] = "🔓"
        else:
            control_loop.lock_reference_cavity()
            st.session_state["cavity_lock"] = "🔐"
    
    cavity_lock.button(label=str(st.session_state["cavity_lock"]), on_click=lock_cavity, key="cavity_lock_button")   

    etalon_tuner.number_input("a", key="etalon_tuner", label_visibility="collapsed", value=round(float(control_loop.etalon_tuner_value),5), format="%0.5f", disabled=etalon_lock_status)
    cavity_tuner.number_input("a", key="cavity_tuner", label_visibility="collapsed", value=round(float(control_loop.reference_cavity_tuner_value),5), format="%0.5f")


    # Wavelength Locker and PID
    tab1.header("Wavelength Locker")
    # wlocker1, wlocker2 = tab1.columns([3.7, 1.3], vertical_alignment="bottom")
    
    if "freq_lock_clicked" not in state:
        state["freq_lock_clicked"] = False
    if "c_wnum" not in state:
        state["c_wnum"] = round(float(control_loop.wavenumber.get()), 5)
        
    def freq_lock():
        if control_loop.reference_cavity_lock_status == "on" and control_loop.etalon_lock_status == "on":
            #print("st locked")
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

        
    with tab1.form("Lock Wavenumber", border=False):
        a1, a2= st.columns([2.7, 1], vertical_alignment="bottom")
        t_wnum = a1.number_input("Target Wavenumber (cm^-1)",  
                                value=state.c_wnum, 
                                step=0.00001, 
                                format="%0.5f",
                                key="t_wnum",                                                                         
                                )
        freq_lock_button = a2.form_submit_button(r"Lock", on_click=freq_lock)

    unlock1, unlock2 = tab1.columns([2.7,1], vertical_alignment="bottom")
    unlock1.empty()
    if not state.freq_lock_clicked:
        unlock1.markdown(":red[_Wavelength Not Locked_]")
    if state.freq_lock_clicked:
        unlock1.markdown(":red[_Wavelength Lock in Progress_]")
        
    freq_unlock_button = unlock2.button(r"Unlock", disabled=not state.freq_lock_clicked, on_click=freq_unlock)

    #PID Control
    initialize_state('kp_enable', False)
    initialize_state('ki_enable', True)
    initialize_state('kd_enable', True)

    def pid_update():
        control_loop.p_update(1. if state.kp_enable else state.kp)
        control_loop.i_update(0. if state.ki_enable else state.ki)
        control_loop.d_update(0. if state.kd_enable else state.kd)

    word1, word2 = tab1.columns([3,1], vertical_alignment="bottom")
    word1.subheader("PID Control")
    word1.write("")
    word2.write("Enable")

    pid1, pid2 = tab1.columns([3,1], vertical_alignment="top")
    with pid2:
        st.write('<div style="height: 28px;">\n</div>', unsafe_allow_html=True)
        kp_enable = st.toggle("p", label_visibility="collapsed", value=not state.kp_enable)
        if kp_enable:
            state.kp_enable = False
            control_loop.p_update(1)
        if not kp_enable:
            state.kp_enable = True
        st.write('<div style="height: 36px;">\n</div>', unsafe_allow_html=True)
        ki_enable = st.toggle("i", label_visibility="collapsed")
        if ki_enable:
            state.ki_enable = False
            control_loop.i_update(0)
        if not ki_enable:
            state.ki_enable = True
        st.write('<div style="height: 38px;">\n</div>', unsafe_allow_html=True)
        kd_enable = st.toggle("d", label_visibility="collapsed")
        if kd_enable:
            state.kd_enable = False
            control_loop.d_update(0)
        if not kd_enable:
            state.kd_enable = True
    
    with pid1.form("PID Control", border=False):
        kp = st.slider("Proportional Gain", min_value=0., max_value=50., value=50., step=0.1, format="%0.2f", key="kp")

        ki = st.slider("Integral Gain", min_value=0., max_value=10., value=0., step=0.1, format="%0.2f", key="ki", disabled=state.ki_enable)

        kd = st.slider("Derivative Gain", min_value=0., max_value=10., value=0., step=0.1, format="%0.2f", key="kd", disabled=state.kd_enable)

        st.form_submit_button("Update", on_click=pid_update)

##################################################################################

    #tab2 - Scan Setttings
    tab2.header("Scan Settings")

    initialize_state("scan_button", False)
    def start_scan():
        if not state.freq_lock_clicked:
            control_loop.start_scan(state.start_wnum, state.end_wnum, state.no_of_steps, state.time_per_scan)
            state.scan_button = True
            st.toast("👀 Scan started!")
        if state.freq_lock_clicked:
            st.toast("👿 Unlock the wavelength first before starting a scan!")
    
    def stop_scan():
        control_loop.stop_scan()
        state.scan_button = False
        st.toast("👀 Scan stopped!")

    initialize_state('centroid_wnum_default', round(float(control_loop.wavenumber.get()), 5))

    def scan_settings():
        c1, c2 = st.columns(2, vertical_alignment='bottom')
        start_wnum = c1.number_input("Start Wavenumber (cm^-1)", 
                                    value=state.centroid_wnum_default,
                                    step=0.00001, 
                                    format="%0.5f",
                                    key="start_wnum"
                                    )
        end_wnum = c2.number_input("End Wavenumber (cm^-1)", 
                                    value=state.centroid_wnum_default,
                                    step=0.00001, 
                                    format="%0.5f",
                                    key="end_wnum"
                                    )
        no_of_steps = c1.number_input("No. of Steps", 
                                    value=5,
                                    max_value=500,
                                    key="no_of_steps"
                                    )
        time_per_scan = c2.number_input("Time per Step (sec)", 
                                        value=2.0,
                                        step=1.,
                                        key="time_per_scan"
                                        )
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
                start_wnum_display, end_wnum_display, scan_range_display, wnum_per_scan = start_wnum * wnum_to_freq, end_wnum * wnum_to_freq, round(scan_range * wnum_to_freq * 1000, 7), round(wnum_per_scan * wnum_to_freq *1000, 7)
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

    with tab2:
        scan_settings()
        button1, button2 = st.columns(2)
        scan_button = button1.button("Start Scan", on_click=start_scan, value=state.scan_button)
        scan_stop = button2.button("Stop Scan",on_click=stop_scan, type="primary", value=not state.scan_button)
    # with tab2.form("scan_settings", border=False):
################################################################################
    #Main body

    #Plotting
    plot = st.empty()
    place1, place2, place3, place4, place5 = st.columns([4, 3, 1, 1, 1], vertical_alignment="center")
    dataf_space = place1.empty()
    reading_rate = place2.empty()
    save_button = place3.button("Save")
    clear_button = place4.button("Clear Plot", key="PLot")
    rerun = place5.button("Rerun", key="main_rerun")

    @st.experimental_dialog("Save As")
    def save_file(data):
        filename = st.text_input("File Name:", placeholder="Enter the file name...")
        filepath = st.text_input("Save to", placeholder="Enter the full path here...")
        if st.button("Save", key="save"):
            try:
                name = f"{filename}.csv"
                path = os.path.join(filepath, name)
                data.to_csv(path, index=False, mode = "x")
                st.success(f"File saved successfully to {path}")
            except Exception as e:
                st.error(f"**Failed to save file due to an error:** {e}")
    
    def clear_plot():
        control_loop.clear_dataset()

    def clear_data():
        control_loop.clear_dataset()

    
    if rerun:
        st.rerun()
    if clear_button:
        clear_plot()
    if save_button:
        save_file(st.session_state.df_toSave)
        clear_data()
    
    loop(plot, dataf_space, reading_rate)

def loop(plot, dataf_space, reading_rate):
    while True:
        if "df_toSave" not in st.session_state:
            st.session_state.df_toSave = None

        try:
            state.control_loop = control_loop
            control_loop.update()
        except Exception as e:
            error_page(description="Unable to update laser information.", error=e)

        # Time series plot
        ts, wn, ts_with_time, wn_with_time = control_loop.xDat, control_loop.yDat, control_loop.xDat_with_time, control_loop.yDat_with_time
        if len(ts) > 0 and len(wn) > 0:
            dataf = pd.DataFrame({"Wavenumber (cm^-1)": wn}, index = ts)
            fig = dataf.iplot(kind="scatter", title = "Wavenumber VS Time", xTitle="Time(s)", yTitle="Wavenumber (cm^-1)", asFigure = True, mode = "lines+markers", colors=["pink"])
            fig.update_xaxes(exponentformat="none")
            fig.update_yaxes(exponentformat="none")
            plot.plotly_chart(fig)
            dataf_space.metric(label="Current Wavenumber", value=wn[-1])
            st.session_state.df_toSave = pd.DataFrame({'Time': ts_with_time, 'Wavenumber': wn_with_time})
            #print(df_toSave)
        
        reading_rate.metric(label="Reading Rate (ms)", value=control_loop.rate)

        sleep_time = control_loop.rate*0.001
        time.sleep(sleep_time)
    


if __name__ == "__main__":
    main()