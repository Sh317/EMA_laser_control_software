from pylablib.devices import M2
import numpy as np
from epics import PV
from .base import ControlLoop
import asyncio
import datetime


class LaserControl(ControlLoop):
    def __init__(self, ip_address, port, wavenumber_pv, gui_callback=None):
        self.laser = M2.Solstis(ip_address, port)
        self.wavenumber = PV(wavenumber_pv)
        self.wnum = round(float(self.wavenumber.get()), 5)
        self.state = 0
        self.scan = 0
        self.xDat = np.array([])
        self.yDat = np.array([])
        self.xDat_with_time = []
        self.yDat_with_time = np.array([])
        self.p = 4.5
        self.target = 0.0
        self.gui_callback = gui_callback
        self.rate = 100  #in milliseconds
        self.now = datetime.datetime.now()
        #A list of commands to be sent to the laser 
        self.reference_cavity_lock_status = self.laser.get_reference_cavity_lock_status()
        self.etalon_lock_status = self.laser.get_etalon_lock_status()
        self.etalon_tuner_value = self.laser.get_full_web_status()['etalon_tune']
        self.reference_cavity_tuner_value = self.laser.get_full_web_status()['cavity_tune']



    def _update(self):
        self.wnum = round(float(self.wavenumber.get()), 5)

#        async def reference_cavity_lock_status(self):
#            self.laser.get_reference_cavity_lock_status()

#        if self.etalon_lock_status == "off" or self.reference_cavity_lock_status == "off":
#            self.unlock()

        if len(self.xDat) == 60:
            self.xDat = np.delete(self.xDat, 0)
            self.yDat = np.delete(self.yDat, 0)
        if len(self.xDat) == 0:
            self.xDat = np.array([0])
            self.xDat_with_time.append(self.now) 
        else:
            self.xDat = np.append(self.xDat, self.xDat[-1] + self.rate)    
            self.xDat_with_time.append(self.xDat_with_time[-1] + self.time_converter(self.rate))
        self.yDat = np.append(self.yDat, self.wnum)
        self.yDat_with_time = np.append(self.yDat_with_time, self.wnum)

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

    def lock_etalon(self):
            self.laser.lock_etalon()

    def unlock_etalon(self):
        self.laser.unlock_etalon()

    def lock_reference_cavity(self):
        self.laser.lock_reference_cavity()

    def unlock_reference_cavity(self):
        self.laser.unlock_reference_cavity()

    def tune_reference_cavity(self, value):
        self.laser.tune_reference_cavity(value)

    def tune_etalon(self, value):
        self.laser.tune_etalon(value)

    def start_scan(self, start, end, no_scans, time_per_scan):
        self.scan_targets = np.linspace(start, end, no_scans)
        self.time_ps = time_per_scan * 1000
        self.target = self.scan_targets[0]
        self.state = 1
        self.scan = 1
        self.do_time = 0
        self.scan_time = 0
        self.j = 0

    def p__update(self, value):
        try:
            self.p = float(value)
        except ValueError:
            self.p = 0

    def time_converter(self, value):
        return datetime.timedelta(milliseconds = value)
    
    def stop(self):
        pass
