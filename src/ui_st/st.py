import streamlit as st
import streamlit_shortcuts as st_shortcuts
import sys
import os
import time
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

def patient_netconnect(tryouts = 10):
    tries = 0
    global control_loop
    while tries <= tryouts:
        try:
            control_loop = LaserControl("192.168.1.222", 39933, f"LaserLab:{tag}")
            break
        except:
            tries += 1
            st.rerun()
    if tries > tryouts:
        raise ConnectionError


def main(): 
    #1/0
    try:
        patient_netconnect()
        control_loop.update()
    except Exception as e:
        st.error("Umm...Something went wrong... at first", icon="🚨")
        e1, e2 = st.columns(2)
        with e1.popover(label="View Error Details"):
            st.write(f"Error: {str(e)}")
        rerun = e2.button("Try Again!", type="primary")
        if rerun:
            st.rerun()

    state = st.session_state
    #sidebar
    tab1, tab2 = sidebar.tabs(["Control", "Scan"])

    #tab1 - Control
    tab1.header("Locks")
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

    #print(control_loop.laser.get_full_status().keys())
    etalon_tuner.number_input("a", key="etalon_tuner", label_visibility="collapsed", value=round(float(control_loop.etalon_tuner_value),5), format="%0.5f", disabled=etalon_lock_status)
    cavity_tuner.number_input("a", key="cavity_tuner", label_visibility="collapsed", value=round(float(control_loop.reference_cavity_tuner_value),5), format="%0.5f", disabled=cavity_lock_status)

    # current wavenumber, target wavenumber, and proportional gain
    #def t_wnum_update():
    #    control_loop.t_wnum_update(st.session_state.t_wnum)
    with tab1.form("Lock Wavenumber", border=False):
        a1, a2= st.columns([4, 1], vertical_alignment="bottom")
        t_wnum = a1.number_input("Target Wavenumber (cm^-1)",  
                                value=round(float(control_loop.wavenumber.get()), 5), 
                                step=0.00001, 
                                format="%0.5f",
                                key="t_wnum",                                                                         
                                )
        freq_lock_button = a2.form_submit_button(r"$\lambda$ Lock")

    #PID Control
    tab1.header("PID Control")
    def p_update():
        control_loop.p_update(st.session_state.p)
    with tab1.form("PID Control", border=False):
        p = st.slider("Proportional Gain", min_value=0., max_value=10., value=4.50, step=0.1, format="%0.2f", key="p")
        st.form_submit_button("Update", on_click=p_update)


    if freq_lock_button:
        if control_loop.reference_cavity_lock_status == "on" and control_loop.etalon_lock_status == "on":
            control_loop.lock(t_wnum)
            st.toast("✅ Wavelength locked!")
        else:
            control_loop.unlock()
            st.toast("❗ Something is not locked ❗")



    #tab2 - Scan Setttings
    tab2.header("Scan Settings")
    def start_scan():
        control_loop.start_scan(start_wnum, end_wnum, no_of_steps, time_per_scan)
        st.toast("👀 Scan started!")

    if "start_wnum" not in state:
        state["start_wnum"] = round(float(control_loop.wavenumber.get()), 5)
    if "end_wnum" not in st.session_state:
        state["end_wnum"] = round(float(control_loop.wavenumber.get()), 5)

    with tab2.form("scan_settings", border=False):
        c1, c2 = st.columns(2, vertical_alignment='bottom')

        start_wnum = c1.number_input("Start Wavenumber (cm^-1)", 
                                    value=state.start_wnum,
                                    step=0.00001, 
                                    format="%0.5f"
                                    )
        end_wnum = c2.number_input("End Wavenumber (cm^-1)", 
                                    value=state.end_wnum,
                                    step=0.00001, 
                                    format="%0.5f"
                                    )
        no_of_steps = c1.number_input("No. of Steps", 
                                    value=5,
                                    max_value=50
                                    )
        time_per_scan = c2.number_input("Time per scan (sec)", 
                                        value=2.0,
                                        step=0.1
                                        )
        scan_button = st.form_submit_button("Start Scan", on_click=start_scan)


    #Main body

    #Plotting
    plot = st.empty()
    place1, place2, place3 = st.columns(3, vertical_alignment="center")
    dataf_space = place1.empty()
    reading_rate = place2.empty()
    save_button = place3.button("Save")


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
    

    if save_button:
        save_file(st.session_state.df_toSave)
        st.stop()

        
    while True:
        if "df_toSave" not in st.session_state:
            st.session_state.df_toSave = None
        try:
            control_loop.update()
        except Exception as e:
            st.error("Umm...Something went wrong in the loop...", icon="🚨")
            e1, e2 = st.columns(2)
            with e1.popover(label="View Error Details"):
                st.write(f"Error: {str(e)}")
            rerun = e2.button("Try Again!", type="primary")
            if rerun:
                st.rerun()

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
        
        time.sleep(0.1)
        


if __name__ == "__main__":
    main()