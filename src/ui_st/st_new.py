import streamlit as st
import streamlit_shortcuts as st_shortcuts
import sys
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
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


    #1/0
try:
    patient_netconnect()
    control_loop.update()
except Exception as e:
    st.error("Umm...Something went wrong...", icon="🚨")
    e1, e2 = st.columns(2)
    with e1.popover(label="View Error Details"):
        st.write(f"Error: {str(e)}")
    rerun = e2.button("Try Again!", type="primary")
    if rerun:
        st.rerun()

##############################################################################
    #Main body
class UI_main():
    def __init__(self, f_main, f_col1, f_col2, f_col3):
        self.main = st.empty()
        c1, c2, c3 = st.columns(3, vertical_alignment="center")
        self.col1, self.col2, self.col3 = c1.empty(), c2.empty(), c3.empty()
        self.f_main, self.f_col1, self.f_col2, self.f_col3 = f_main, f_col1, f_col2, f_col3
    
    def display_f_main(self):
        with self.main:
            self.f_main.execute()
    def display_f_col1(self):
        with self.col1:
            self.f_col1.execute()
    def display_f_col2(self):
        with self.col2:
            self.f_col2.execute()
    def display_f_col3(self):
        with self.col3:
            self.f_col3.execute()

# class LaserInfo():
#     def __init__(self, control_loop):
#         self.ts, self.wn, self.ts_with_time, self.wn_with_time = control_loop.xDat, control_loop.yDat, control_loop.xDat_with_time, control_loop.yDat_with_time

class Functions(ABC):
    @abstractmethod
    def execute(self):
        pass

class Plot(Functions):
    def __init__(self, ts, wn):
        self.ts = ts
        self.wn = wn
    
    def execute(self):
        if len(self.ts) > 0 and len(self.wn) > 0:
            dataf = pd.DataFrame({"Wavenumber (cm^-1)": self.wn}, index = self.ts)
            fig = dataf.iplot(kind="scatter", title = "Wavenumber VS Time", xTitle="Time(s)", yTitle="Wavenumber (cm^-1)", asFigure = True, mode = "lines+markers", colors=["pink"])
            fig.update_xaxes(exponentformat="none")
            fig.update_yaxes(exponentformat="none")
        st.plotly_chart(fig)

class Live_wl(Functions):
    def __init__(self, wn):
        self.wn = wn
    
    def execute(self):
        st.metric(label="Current Wavenumber", value=self.wn[-1])

class Reading_rate(Functions):
    def __init__(self, rate):
        self.rate = rate
    
    def execute(self):
        st.metric(label="Reading Rate (ms)", value=self.rate)

class Save(Functions):
    def __init__(self, df):
        self.df = df

    @st.experimental_dialog("Save As")
    def __save_file(self, data):
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

    def execute(self):
        save_button = st.button("Save")
        if save_button:
            self.__save_file(self.df)
            st.stop()

    
def main():
    ts, wn, ts_with_time, wn_with_time, rate = control_loop.xDat, control_loop.yDat, control_loop.xDat_with_time, control_loop.yDat_with_time, control_loop.rate
    df = None
    plot = Plot(ts, wn)
    live_wl = Live_wl(wn)
    reading_rate = Reading_rate(rate)
    save = Save(df)
    ui_main = UI_main(plot, live_wl, reading_rate, save)
    ui_main.display_f_main()

    # while True:
    #     try:
    #         control_loop.update()
    #     except Exception as e:
    #         st.error("Umm...Something went wrong...", icon="🚨")
    #         e1, e2 = st.columns(2)
    #         with e1.popover(label="View Error Details"):
    #             st.write(f"Error: {str(e)}")
    #         rerun = e2.button("Try Again!", type="primary")
    #         if rerun:
    #             st.rerun()

    #     ts, wn, ts_with_time, wn_with_time, rate = control_loop.xDat, control_loop.yDat, control_loop.xDat_with_time, control_loop.yDat_with_time, control_loop.rate
    #     if "df_toSave" not in st.session_state:
    #         st.session_state.df_toSave = None
    #     st.session_state.df_toSave = pd.DataFrame({'Time': ts_with_time, 'Wavenumber': wn_with_time})

    #     ui_main.f_main = Plot(ts, wn)
    #     ui_main.display_f_main()
    #     ui_main.f_col1 = Live_wl(wn)
    #     ui_main.display_f_col1()
    #     ui_main.f_col2 = Reading_rate(rate)
    #     ui_main.display_f_col2()
    #     ui_main.f_col3 = Save(st.session_state.df_toSave)
    #     ui_main.display_f_col3()

    #     time.sleep(0.1)



if __name__ == "__main__":
    main()