import streamlit as st
import streamlit_shortcuts as st_shortcuts
import sys
import time
import numpy as np
import plotly.graph_objects as go
import pandas as pd

sys.path.append('.\\src')
from control.st_laser_control import LaserControl




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
control_loop = LaserControl("192.168.1.222", 39933, f"LaserLab:{tag}")


def main(): 
    #1/0
    try:
        control_loop.update()
    except Exception as e:
        st.error("Umm...Something went wrong...", icon="🚨")
        e1, e2 = st.columns(2)
        with e1.popover(label="View Error Details"):
            st.write(f"Error: {str(e)}")
        rerun = e2.button("Try Again!", type="primary")
        if rerun:
            st.rerun()

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
        return "🔐" if  e_status == "on" else "🔓"
    
    if "etalon_lock" not in st.session_state:
        st.session_state["etalon_lock"] = etalon_lock_status()

    
    def lock_etalon():
        if control_loop.etalon_lock_status == "on":
            control_loop.unlock_etalon()
            st.session_state["etalon_lock"] = "🔓"
        if control_loop.etalon_lock_status == "off":
            control_loop.lock_etalon()
            st.session_state["etalon_lock"] = "🔐"


    etalon_lock.button(label=str(st.session_state["etalon_lock"]), on_click=lock_etalon, key="etalon_lock_button")
    
    def cavity_lock_status():
        c_status = control_loop.reference_cavity_lock_status
        assert isinstance(c_status, str) and c_status in ["on", "off"], f"Invalid cavity lock status: {c_status}"
        return "🔐" if  c_status == "on" else "🔓"
    
    if "cavity_lock" not in st.session_state:
        st.session_state["cavity_lock"] = cavity_lock_status()
    

    def lock_cavity():
        if control_loop.reference_cavity_lock_status == "on":
            control_loop.unlock_reference_cavity()
            st.session_state["cavity_lock"] = "🔓"
        if control_loop.reference_cavity_lock_status == "off":
            control_loop.lock_reference_cavity()
            st.session_state["cavity_lock"] = "🔐"
    
    cavity_lock.button(label=str(st.session_state["cavity_lock"]), on_click=lock_cavity, key="cavity_lock_button")   

    #print(control_loop.laser.get_full_status().keys())
    etalon_tuner.number_input("a", key="etalon_tuner", label_visibility="collapsed", value=round(float(control_loop.etalon_tuner_value),5),format="%0.5f")
    cavity_tuner.number_input("a", key="cavity_tuner", label_visibility="collapsed", value=round(float(control_loop.reference_cavity_tuner_value),5),format="%0.5f")

    # current wavenumber, target wavenumber, and proportional gain
    #def t_wnum_update():
    #    control_loop.t_wnum_update(st.session_state.t_wnum)
    a1, a2= tab1.columns([4, 1], vertical_alignment="bottom")
    t_wnum = a1.number_input("Target Wavenumber (cm^-1)",  
                            value=round(float(control_loop.wavenumber.get()), 5), 
                            step=0.00001, 
                            format="%0.5f",
                            key="t_wnum",                                                                         
                            )
    freq_lock_toggle = a2.button("$\lambda$ Lock", key="freq_lock")

    def p_update():
        control_loop.p_update(st.session_state.p)
    # p = col1.number_input("Proportional Gain", 
    #                             value=4.50,
    #                             step=0.01, 
    #                             format="%0.2f",
    #                             key="p",
    #                             on_change=p_update
    #                             )
    p = tab1.slider("Proportional Gain", min_value=0., max_value=10., value=4.50, step=0.1, format="%0.2f", key="p")


    if freq_lock_toggle:
        if control_loop.reference_cavity_lock_status == "on" and control_loop.etalon_lock_status == "on":
            control_loop.lock(t_wnum)
        else:
            control_loop.unlock()
            st.toast("Something is not locked!")

    #tab2 - Scan Setttings
    c1, c2 = tab2.columns(2, vertical_alignment='bottom')
    scan_button = c1.empty()
    c2.write("")
    start_wnum = c1.number_input("Start Wavenumber (cm^-1)", 
                                value=round(float(control_loop.wavenumber.get()), 5),
                                step=0.00001, 
                                format="%0.5f"
                                )
    end_wnum = c2.number_input("End Wavenumber (cm^-1)", 
                                value=round(float(control_loop.wavenumber.get()), 5),
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
    def start_scan():
        control_loop.start_scan(start_wnum, end_wnum, no_of_steps, time_per_scan)
        st.toast("Scan started!")
    scan_button.button("Start Scan", on_click=start_scan)


    #Main body

    #Plotting
    plot = st.empty()
    dataf_space = st.empty()

    while True:
        control_loop.update()
        # c_wnum.metric(label="Current Wavenumber (cm^-1)", value=round(float(control_loop.wavenumber.get()), 5))
        # Time series plot
        ts, wn = control_loop.xDat, control_loop.yDat
        if len(ts) > 0 and len(wn) > 0:
            dataf = pd.DataFrame({"Wavenumber (cm^-1)": wn, "Time (sec)": ts})
            fig = go.Figure(data=go.Scatter(x=ts, y=wn), layout=go.Layout(
                xaxis=dict(title="time"), yaxis=dict(title="wavenumber", exponentformat="none")
                ))
            plot.plotly_chart(fig, use_container_width=True)
            dataf_space.metric(label="Current Wavenumber", value=wn[-1])

        time.sleep(0.1)
        

if __name__ == "__main__":
    main()