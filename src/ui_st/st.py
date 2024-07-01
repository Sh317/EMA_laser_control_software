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

# Select which laser to control
i = sidebar.selectbox("Select Laser", ["Laser 1", "Laser 2", "Laser 3", "Laser 4"], index=0)

l1, l2, l3 = sidebar.columns([1.5,1,1])
lock_toggle = l1.toggle("Lock", key="lock")
etalon_state = l2.empty()
cavity_state = l3.empty()

tag = f"wavenumber_{i.split(" ")[1]}"

# Initialize plot and data storage
xDat = np.array([])
yDat = np.array([])
fig = go.Figure()

def update_plot(fig, xDat, yDat):
    fig.data = []  # Clear existing data
    fig.add_trace(go.Scatter(x=xDat, y=yDat, mode='lines', name='Wavenumber'))
    return fig

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


    # Current wavenumber, target wavenumber, and proportional gain
    def p_update():
        control_loop.p_update(st.session_state.p)
    # c_wnum = col1.empty()

    t_wnum = sidebar.number_input("Target Wavenumber (cm^-1)",  
                            value=round(float(control_loop.wavenumber.get()), 5), 
                            step=0.00001, 
    c_wnum = col1.empty()
    t_wnum = col2.number_input("Target Wavenumber (cm^-1)",
                            value=round(float(control_loop.wavenumber.get()), 5),
                            step=0.00001,
        e_status = asyncio.run(control_loop.etalon_lock_status())
        assert isinstance(e_status, str) and e_status in ["on", "off"], f"Invalid etalon lock status: {e_status}"
        return "🔐" if  e_status == "on" else "🔓"

    def cavity_lock_status():
        c_status = control_loop.reference_cavity_lock_status
        assert isinstance(c_status, str) and c_status in ["on", "off"], f"Invalid etalon lock status: {c_status}"
        return "🔐" if  c_status == "on" else "🔓"
        
    etalon_state.metric("Etalon", value=etalon_lock_status())
    cavity_state.metric("Cavity", value=cavity_lock_status())


    if lock_toggle:
        if control_loop.reference_cavity_lock_status == "on" and asyncio.run(control_loop.etalon_lock_status()) == "on":
            control_loop.lock(t_wnum)
        else:
            control_loop.unlock()
            st.toast("Something is not locked!")

    # Scan settings
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
    plot = st.empty()
    dataf_space = st.empty()
    mkspace = st.empty()

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

    
        mkspace.markdown("""
                Laboratory of Exotic Molecules and Atoms @ MIT
                Our group is focused on the study of atoms and molecules containing short-lived radioactive nuclei for fundamental physics research. Precision measurements of their atomic and molecular structures provide a unique insight into the emergence of nuclear phenomena and the properties of nuclear matter at the limits of existence. Moreover, these radioactive systems have the potential to offer a new window for our exploration of the fundamental forces of nature and the search for new physics beyond the Standard Model of particle physics.
                       """)
        time.sleep(0.1)
        

if __name__ == "__main__":
    main()
