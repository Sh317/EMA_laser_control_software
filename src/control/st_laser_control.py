from pylablib.devices import M2
import numpy as np
from epics import PV
from .base import ControlLoop
import datetime
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
        self.laser = None
        self.ip_address = ip_address
        self.port = port    
        self.patient_laser_init()
        self.wavenumber = PV(wavenumber_pv)
        self.wnum = None
        self.state = 0
        self.scan = 0
        self.xDat = np.array([])
        self.yDat = np.array([])
        self.xDat_with_time = []
        self.yDat_with_time = np.array([])
        self.p = 4.5
        self.target = 0.0
        self.rate = 100.  #in milliseconds
        self.conversion = 80
        self.now = datetime.datetime.now()
        self.pid = PIDController(kp=4.5, ki=0., kd=0., setpoint=self.target)######
        #A list of commands to be sent to the laser 
        self.patient_setup_status()

    def patient_laser_init(self, tryouts = 2) -> None:
        laser_set = 0
        tries = 0
        if self.laser:
            pass
        while not laser_set:
            try:
                self.laser = M2.Solstis(self.ip_address, self.port)
                laser_set = True
                break
            except Exception as e:
                print(f"Unable to connect to laser. Retrying... Error: {e}")
                print(tries)
                if tries >= tryouts:
                    print(f"Unable to connect to laser after {tryouts} tries. Error: {e}")
                    raise ConnectionRefusedError
                else:
                    tries += 1

    def patient_setup_status(self, tryouts = 2) -> None:
        if not self.laser:
            raise ConnectionError
        status_set = 0
        tries = 0
        while not status_set:
            try:
                self.reference_cavity_lock_status = self.laser.get_reference_cavity_lock_status()
                self.etalon_lock_status = self.laser.get_etalon_lock_status()
                self.etalon_tuner_value = self.laser.get_full_web_status()['etalon_tune']
                self.reference_cavity_tuner_value = self.laser.get_full_web_status()['cavity_tune']
                status_set = True
                break
            except Exception as e:
                print(f"Unable to get patient setup status. Retrying... Error: {e}")
                print(tries)
                if tries >= tryouts:
                    print(f"Unable to set patient setup status after {tryouts} tries. Error: {e}")
                    raise ConnectionRefusedError
                else:
                    tries += 1
    
    def patient_update(self):
        try:
            self.reference_cavity_lock_status = self.laser.get_reference_cavity_lock_status()
            self.etalon_lock_status = self.laser.get_etalon_lock_status()
            self.etalon_tuner_value = self.laser.get_full_web_status()['etalon_tune']
            self.reference_cavity_tuner_value = self.laser.get_full_web_status()['cavity_tune']
        except Exception as e:
            print(f"Unable to acquire laser information. Error: {e}")
            raise ConnectionRefusedError

    def _update(self):
        #print(self.state)
        self.wnum = round(float(self.wavenumber.get()), 5)
        self.patient_update()

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

        if self.scan == 1:
            self._do_scan()

        if self.state == 1:
            print("locked")
            #set the wavelength to the target
            if self.init == 1:
                delta = self.target - self.wnum
                delta *= self.conversion
                self.laser.tune_reference_cavity(float(self.reference_cavity_tuner_value) - delta)
                self.init = 0
                print("wavelength set")
            else:
                # Simple proportional control
                # delta = self.target - self.wnum
                # u = self.p * delta
                self.pid.setpoint = self.target
                u = self.pid.update(self.wnum)
                self.laser.tune_reference_cavity(float(self.reference_cavity_tuner_value) - u)
                print(f"target:{self.target}")
                print(f"current:{self.wnum}")
                print(f"correction:{u}")
                # print("wavelength in control")
                
            # self.laser.tune_reference_cavity(float(self.reference_cavity_tuner_value) - u)

    
    def update(self):
        try:
            self._update()
        except Exception as e:
            print(f"Error in LaserControl._update: {e}")
            pass

    def lock(self, value):
        self.state = 1
        print(f"lock function called with state being {self.state}")
        self.target = value
        self.init = 1
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
        self.time_ps = time_per_scan
        self.scan_time = time_per_scan
        self.state = 1
        self.scan = 1
        self.j = 0
    
    def stop_scan(self):
        self.scan = 0
        self.state = 0
    
    def _do_scan(self):
        try:
            if self.scan_time >= self.time_ps:
                self.target = self.scan_targets[self.j]
                self.init = 1
                #initialize, and one step forward
                self.scan_time = 0
                self.j += 1
            else:
                self.scan_time += self.rate*0.001
                print(self.scan_time)
                #to convert rate to seconds

        except IndexError:
            self.scan = 0
            self.state = 0

    def p_update(self, value):
        try:
            self.pid.kp = float(value)
        except ValueError:
            self.pid.kp = 0

    def i_update(self, value):
        try:
            self.pid.ki = float(value)
        except ValueError:
            self.pid.ki = 0
    
    def d_update(self, value):
        try:
            self.pid.kd = float(value)
        except ValueError:
            self.pid.kd = 0

    def time_converter(self, value):
        return datetime.timedelta(milliseconds = value)
    
    def stop(self):
        pass
