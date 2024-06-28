from pylablib.devices import M2
import numpy as np
import plotly.graph_objects as go
from epics import PV
from .base import ControlLoop
import asyncio


class LaserControl(ControlLoop):
    def __init__(self, ip_address, port, wavenumber_pv, gui_callback=None):
        self.laser = M2.Solstis(ip_address, port)
        self.wavenumber = PV(wavenumber_pv)
        self.wnum = round(float(self.wavenumber.get()), 5)
        self.state = 0
        self.scan = 0
        self.xDat = np.array([])
        self.yDat = np.array([])
        self.p = 4.5
        #self.t_wnum = 0
        self.target = 0.0
        self.gui_callback = gui_callback      
    async def etalon_lock_status(self):
        self.etalon_lock_status = self.laser.get_etalon_lock_status()
        return self.etalon_lock_status
    
    def _update(self):
        self.wnum = round(float(self.wavenumber.get()), 5)

#        async def reference_cavity_lock_status(self):
#            self.laser.get_reference_cavity_lock_status()
        self.reference_cavity_lock_status = self.laser.get_reference_cavity_lock_status()

#        if self.etalon_lock_status == "off" or self.reference_cavity_lock_status == "off":
#            self.unlock()

        if len(self.xDat) == 60:
            self.xDat = np.delete(self.xDat, 0)
            self.yDat = np.delete(self.yDat, 0)
        if len(self.xDat) == 0:
            self.xDat = np.array([0])
        else:
            self.xDat = np.append(self.xDat, self.xDat[-1] + 100)
        self.yDat = np.append(self.yDat, self.wnum)
        self.fig = go.Figure(data=go.Scatter(x=self.xDat, y=self.yDat))

        if self.state == 1:

            # Simple proportional control
            delta = self.target - self.wnum
            u = self.p * delta
            cavity = self.laser.get_full_status(include=["web_status"])["web_status"][
                "cavity_tune"
            ]
            self.laser.tune_reference_cavity(float(cavity) - u)

            if self.gui_callback:
                self.gui_callback(self.wnum, self.xDat, self.yDat)
            #what is this for?

        if self.scan == 1:
            delta = self.target - self.wnum
            if abs(delta) <= 0.00005 and not self.do_time:
                self.do_time = 1
            if self.do_time:
                self.scan_time += 100
            if self.scan_time == self.time_ps:
                self.j += 1
                self.scan_time = 0
                try:
                    self.target = self.scan_targets[self.j]
                    self.do_time = 0
                except IndexError:
                    self.scan = 0
                    self.state = 0
    
    def update(self):
        try:
            self._update()
        except Exception as e:
            print(f"Error in LaserControl._update: {e}")
            pass

    def lock(self, value):
        self.state = 1
        self.target = value
        self.xDat = np.array([])
        self.yDat = np.array([])

    def unlock(self):
        self.state = 0
        self.scan = 0
        self.xDat = np.array([])
        self.yDat = np.array([])

    def start_scan(self, start, end, no_scans, time_per_scan):
        self.scan_targets = np.linspace(start, end, no_scans)
        self.time_ps = time_per_scan * 1000
        self.target = self.scan_targets[0]
        self.state = 1
        self.scan = 1
        self.do_time = 0
        self.scan_time = 0
        self.j = 0

    def stop(self):
        pass

    #def t_wnum_update(self, value):
    #    try:
    #        self.t_wnum = float(value)
    #    except ValueError:
    #        self.twnum = 0

    def p__update(self, value):
        try:
            self.p = float(value)
        except ValueError:
            self.p = 0

