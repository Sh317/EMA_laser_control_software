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
        self.scan_progress = 0.
        self.rate = 100.  #in milliseconds
        self.conversion = 60
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
        self.wnum = round(float(self.wavenumber.get()), 5)
        #print(self.wnum)

        if len(self.xDat) == 60:
            self.xDat = np.delete(self.xDat, 0)
            self.yDat = np.delete(self.yDat, 0)
        if len(self.xDat) == 0:
            self.xDat = np.array([0])
        else:
            self.xDat = np.append(self.xDat, self.xDat[-1] + self.rate*0.001)    

        if len(self.xDat_with_time) == 0:
            self.xDat_with_time.append(self.now) 
        else:
            self.xDat_with_time.append(self.xDat_with_time[-1] + self.time_converter(self.rate))

        self.yDat = np.append(self.yDat, self.wnum)
        self.yDat_with_time = np.append(self.yDat_with_time, self.wnum)

        if self.scan == 1:
            self._do_scan()

        if self.state == 1:
        #lock-in the wavelength of laser mode
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
                self.pid_filtered_control(self.wnum, self.target)
                # print(f"target:{self.target}")
                # print(f"current:{self.wnum}")
                # print(f"correction:{u}")
                # print("wavelength in control")
            
        if self.state == 2:
        #get conversion constant mode
            self.do_conversion()

    def update(self):
        try:
            self._update()
        except Exception as e:
            print(f"Error in LaserControl._update: {e}")
            pass
    
    def get_conversion(self):
        self.state = 2

    def do_conversion(self):
        list = np.linspace(10, 100, 10)
        loop = 0
        loopend = 5
        delta = 0.001
        closest = np.array([])
        wnum = np.array([])
        while loop < loopend:
            output_deltas = np.array([])
            for i in list:
                input_wnum = round(float(self.wavenumber.get()), 5)
                i = round(i,0)    
                u = i * delta
                self.laser.tune_reference_cavity(float(self.reference_cavity_tuner_value) - u)                
                output_wnum = round(float(self.wavenumber.get()), 5)
                output_delta = np.abs(output_wnum - input_wnum)
                output_deltas = np.append(output_deltas, output_delta)
                # print(i)
                # print(output_delta)
                #time.sleep(0.1)
            closest_index = np.abs(output_deltas - delta).argmin()
            closest_number = list[closest_index]
            closest = np.append(closest, closest_number)
            wnum = np.append(wnum, output_deltas[closest_index])
            print(f"best:{closest_number}")
            print(f"length:{len(list)- len(output_deltas)}")
            loop += 1
            
        print(f"wavelength:{wnum}")
        print(closest)
        self.state = 0
    
    def hack_reading_rate(self):
        rates = np.linspace(150, 1, 150)
        effective_rates = np.array([])
        loop = 0
        loop_end = 100
        while loop < loop_end:
            print(f"In {loop} loop now")
            for rate in rates:
                first = round(float(self.wavenumber.get()), 5)
                # time.sleep(rate*0.001)
                second = round(float(self.wavenumber.get()), 5)
                if first == second:
                    effective_rates = np.append(effective_rates, rate)
                    break
                else: pass
            loop += 1

        unique, counts = np.unique(effective_rates, return_counts=True)
        most_frequent_index = counts.argmax()
        most_frequent_number = unique[most_frequent_index]
        print(f"most frequent reading rate: {most_frequent_number} ms")
        print(f"potential list: {unique}")

    def pid_control(self):
        self.pid.setpoint = self.target
        u = self.pid.update(self.wnum)
        self.laser.tune_reference_cavity(float(self.reference_cavity_tuner_value) - u)

    def pid_filtered_control(self, current, target):
        lower = target - 0.00002
        upper = target + 0.00002
        if current >= lower and current <= upper:
            pass
        else: 
            self.pid_control()

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
        self.time_ps = round(time_per_scan, 5)
        self.scan_time = round(time_per_scan, 5)
        self.state = 1
        self.scan = 1
        self.j = 0
        self.jmax = no_scans
        self.scan_progress = 0.
    
    def stop_scan(self):
        self.scan = 0
        self.state = 0

    def end_scan(self):
        self.scan = 0
        self.state = 0
        self.scan_progress = 100.
    
    def _do_scan(self):
        try:
            self.scan_progress += 1
            if self.scan_time >= self.time_ps:
                if self.j < self.jmax:
                    self.target = self.scan_targets[self.j]
                    self.init = 1
                    #initialize, and one step forward
                    self.scan_time = 0
                    self.j += 1
                else: 
                    self.end_scan()
            else:
                self.scan_time += round(self.rate*0.001, 5)
                print(self.scan_time)
                #to convert rate to seconds
        except IndexError:
            self.scan = 0
            self.state = 0

    def scan_update(self, new_time_ps):
        self.time_ps = new_time_ps
    
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

    def clear_plot(self):
        self.xDat = np.array([])
        self.yDat = np.array([])
    
    def clear_dataset(self):
        self.xDat_with_time = []
        self.yDat_with_time = np.array([])

    
    def stop(self):
        pass
