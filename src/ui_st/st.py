import streamlit as st
import sys
import time
import numpy as np

sys.path.append('.\\src')
from control.st_laser_control import LaserControl




st.set_page_config(
    page_title="Laser Control System",
    page_icon=":mirror:",
    layout="wide",
)

st.title("Laser Control System")

sidebar = st.sidebar

# select which laser to control
i = sidebar.selectbox("Select Laser", ["Laser 1", "Laser 2", "Laser 3", "Laser 4"], index=2)
tag = f"wavenumber_{i.split(" ")[1]}"
control_loop = LaserControl("192.168.1.222", 39933, f"LaserLab:{tag}")


try:

    1/0
    control_loop.update()

    #locks
    col1, col2 = st.columns(2, vertical_alignment="top")

    etalon_on = col1.empty()
    cavity_on = col2.empty()    

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
    p = col1.number_input("Proportional Gain", 
                                value=4.50,
                                step=0.01, 
                                format="%0.2f",
                                key="p",
                                on_change=p_update
                                )

    #etalon and cavity locks callback
    def etalon_lock_status():
        if control_loop.etalon_lock_status == "on":
            return True
        if control_loop.etalon_lock_status == "off":
            return False

    def cavity_lock_status():
        if control_loop.reference_cavity_lock_status == "on":
            return True
        if control_loop.reference_cavity_lock_status == "off":
            return False
        
    etalon_on.toggle("Etalon Lock", value=etalon_lock_status())
    if etalon_on:
        control_loop.lock(t_wnum)

    cavity_on.toggle("Cavity Lock", value=cavity_lock_status())
    if cavity_on:
        control_loop.lock(t_wnum)

    #scan setttings
    c1, c2, c3, c4 = st.columns(4, vertical_alignment='bottom')
    c1.header("Scan Settings", divider="gray")
    c2.write("")
    c3.write("")
    scan_button = c4.empty()
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
    no_of_steps = c3.number_input("No. of Steps", 
                                value=5,
                                max_value=50
                                )
    time_per_scan = c4.number_input("Time per scan (sec)", 
                                    value=2.0,
                                    step=0.1
                                    )
    def start_scan():
        control_loop.start_scan(start_wnum, end_wnum, no_of_steps, time_per_scan)
    scan_button.button("Start Scan", on_click=start_scan)

    #Plotting
    st.markdown("Plot")
    plot = st.empty()



    # placeholder for updating live parameters
    placeholder = st.empty()

    while True:
        control_loop.update()
        c_wnum.metric(label="Current Wavenumber (cm^-1)", value=round(float(control_loop.wavenumber.get()), 5))
        #print(round(float(control_loop.wavenumber.get()), 5))
        plot.line_chart(control_loop.dataToPlot, x_label="Indices", y_label="Wavenumber (cm^-1)", width=800, height=400)
        time.sleep(1)

except Exception as e:
    st.error("Umm...Something went wrong...", icon="🚨")
    e1, e2 = st.columns(2)
    with e1.popover(label="View Error Details"):
        st.write(f"Error: {str(e)}")
    rerun = e2.button("Try Again!", type="primary")
    if rerun:
        st.rerun()