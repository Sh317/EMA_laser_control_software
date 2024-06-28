import streamlit as st
import sys
import time
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import asyncio

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

    #locks
    col1, col2, col3 = st.columns(3, vertical_alignment="top")

    etalon_status = col1.empty()
    cavity_status = col2.empty()
    lock_toggle = col3.empty()    

    # current wavenumber, target wavenumber, and proportional gain
    #def t_wnum_update():
    #    control_loop.t_wnum_update(st.session_state.t_wnum)
    def p_update():
        control_loop.p_update(st.session_state.p)
    c_wnum = col1.empty()
    #print(round(float(control_loop.wavenumber.get()), 5))
    t_wnum = col2.number_input("Target Wavenumber (cm^-1)",  
                            value=round(float(control_loop.wavenumber.get()), 5), 
                            step=0.00001, 
                            format="%0.5f",
                            key="t_wnum",                          
    #                        on_change=t_wnum_update                                               
                            )
    # p = col1.number_input("Proportional Gain", 
    #                             value=4.50,
    #                             step=0.01, 
    #                             format="%0.2f",
    #                             key="p",
    #                             on_change=p_update
    #                             )
    p = sidebar.slider("Proportional Gain", min_value=0., max_value=10., value=4.50, step=0.1, format="%0.2f", key="p")

    #etalon and cavity locks callback
    def etalon_lock_status():
        status = asyncio.run(control_loop.etalon_lock_status())
        assert isinstance(status, str) and status in ["on", "off"], f"Invalid etalon lock status: {status}"
        return "🔒" if  status == "on" else "🔓"

    def cavity_lock_status():
        if control_loop.reference_cavity_lock_status == "on":
            return "🔒"
        if control_loop.reference_cavity_lock_status == "off":
            return "🔓"
        
    etalon_status.metric("Etalon", value=etalon_lock_status())
    cavity_status.metric("Cavity", value=cavity_lock_status())

    lock_toggle.toggle("Lock")
    if lock_toggle:
        if control_loop.reference_cavity_lock_status == "on" and asyncio.run(control_loop.etalon_lock_status()) == "on":
            control_loop.lock(t_wnum)
        else:
            control_loop.unlock()
            st.toast("Something is not locked!")

    #scan setttings
    with sidebar.expander("Scan Settings"):
        c1, c2 = st.columns(2, vertical_alignment='bottom')
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

    #Plotting
    plotHolder = st.empty()

    while True:
        control_loop.update()
        c_wnum.metric(label="Current Wavenumber (cm^-1)", value=round(float(control_loop.wavenumber.get()), 5))
        #print(round(float(control_loop.wavenumber.get()), 5))
        plotHolder.plotly_chart(control_loop.fig)
        time.sleep(0.1)

if __name__ == "__main__":
    main()