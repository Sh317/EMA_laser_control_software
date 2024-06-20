import numpy as np
from .base import ControlLoop
from pylablib.devices import M2
from epics import PV
import time

class PIDController:
    def __init__(self, kp, ki, kd, setpoint):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.integral = 0
        self.previous_error = 0
        self.previous_time = time.time()

    def update(self, current_value):
        current_time = time.time()
        delta_time = current_time - self.previous_time
        error = self.setpoint - current_value

        self.integral += error * delta_time
        derivative = (error - self.previous_error) / delta_time

        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)

        self.previous_error = error
        self.previous_time = current_time

        return output

class LaserControl(ControlLoop):
    def __init__(self, ip_address, port, wavenumber_pv):
        self.laser = M2.Solstis(ip_address, port)
        self.wavenumber = PV(wavenumber_pv)
        self.state = 0
        self.scan = 0
        self.xDat = np.array([])
        self.yDat = np.array([])
        self.p = 4.5
        self.target = 0.0

        # PID controller parameters
        self.pid = PIDController(kp=1.0, ki=0.1, kd=0.05, setpoint=self.target)

    def update(self):
        self.wnum = round(float(self.wavenumber.get()), 5)
        etalon_lock_status = self.laser.get_etalon_lock_status()
        reference_cavity_lock_status = self.laser.get_reference_cavity_lock_status()

        if etalon_lock_status == 'off' or reference_cavity_lock_status == 'off':
            self.unlock()

        if self.state == 1:
            if len(self.xDat) == 60:
                self.xDat = np.delete(self.xDat, 0)
                self.yDat = np.delete(self.yDat, 0)
            self.xDat = np.append(self.xDat, self.xDat[-1] + 100)
            self.yDat = np.append(self.yDat, self.wnum)

            # Update PID controller with the current wavenumber
            control_output = self.pid.update(self.wnum)
            cavity = self.laser.get_full_status(include=['web_status'])['web_status']['cavity_tune']
            self.laser.tune_reference_cavity(float(cavity) - control_output)

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
                    self.pid.setpoint = self.target
                    self.do_time = 0
                except IndexError:
                    self.scan = 0
                    self.state = 0

    def lock(self):
        self.state = 1
        self.target = self.wl.value()
        self.pid.setpoint = self.target
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
        self.pid.setpoint = self.target
        self.state = 1
        self.scan = 1
        self.do_time = 0
        self.scan_time = 0
        self.j = 0

    def stop(self):
        pass

    def p_update(self, value):
        try:
            self.pid.kp = float(value)
        except ValueError:
            self.pid.kp = 0
