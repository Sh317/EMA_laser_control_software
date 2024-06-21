import streamlit as st
import sys

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
i = sidebar.selectbox("Select Laser", ["Laser 1", "Laser 2", "Laser 3", "Laser 4"])
tag = f"wavenumber_{i.split(" ")[1]}"
control_loop = LaserControl("192.168.1.222", 39933, f"LaserLab:{tag}")

#locks
col1, col2 = st.columns(2)

control_loop.update()
etalon_on = col1.toggle("Etalon Lock")
if etalon_on:
    control_loop.lock()
    st.write(":locked:")

cavity_on = col2.toggle("Cavity Lock")

if cavity_on:
    control_loop.lock()
    st.write(":locked:")

# current wavenumber, target wavenumber, and proportional gain
def t_wnum_update():
    control_loop.t_wnum_update(st.session_state.t_wnum)
def p_update():
    control_loop.p_update(st.session_state.p)

c_wnum = col1.number_input("Current Wavenumber", 
                           value=round(float(control_loop.wavenumber.get()), 5), 
                           step=0.00001, 
                           format="%0.5f"
                           )
t_wnum = col2.number_input("Target Wavenumber", 
                           value=round(float(control_loop.wavenumber.get()), 5), 
                           step=0.00001, 
                           format="%0.5f",
                           key="t_wnum",                          
                           on_change=t_wnum_update                                               
                           )
# Question: control_loop.lock() is suppposed to set the laser to the target wavelength which is a input here in the gui. 
# I don't know how to let laser control class access this data.
p = col1.number_input("Proportional Gain", 
                              value=4.50,
                              step=0.01, 
                              format="%0.2f",
                              key="p",
                              on_change=p_update
                              )

