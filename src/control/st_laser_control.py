from pylablib.devices import M2
import numpy as np
from epics import PV
from .base import ControlLoop
import datetime
import time
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pc
import os
import ntplib
from time import ctime
from typing import List, Dict, Any, Optional
import threading
import asyncio
import traceback

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


class EMAServerReader:
    def __init__(self, pv_name: str, saving_dir: str = None, reading_frequency: float = 0.1,
                 write_each: float = 100, ntp_sync_interval: float = 60, verbose: bool = False, plot_limit: int = 60):
        self.name = pv_name
        self.pv = PV(pv_name)
        self.saving_dir = saving_dir
        self.ntp_client = ntplib.NTPClient()
        self.dataframe = pd.DataFrame(columns=['time', 'value'])
        self.write_each = write_each
        self.reading_frequency = reading_frequency
        self.ntp_sync_interval = ntp_sync_interval
        self.date_format = '%a %b %d %H:%M:%S %Y'
        self.verbose = verbose
        self.last_ntp_sync_time = time.time()
        self.offset = 0
        self.xDat = np.array([])
        self.yDat = np.array([])
        self.first_time = 0.
        self.plot_limit = plot_limit
        self.reading_thread = None
        self.is_reading = False
        self.latest_data = None

    def sync_time_with_ntp(self):
        async def sync_time():
            try:
                response = await asyncio.get_event_loop().run_in_executor(None, self.ntp_client.request, 'pool.ntp.org')
                ntp_time = response.tx_time
                self.offset = ntp_time - time.time()
                self.last_ntp_sync_time = time.time()
                if self.verbose:
                    print(f"Time synchronized with NTP. Offset: {self.offset} seconds")
            except Exception as e:
                if self.verbose:
                    print(f"Error syncing time with NTP: {e}")
        
        asyncio.run(sync_time())
                        

    def get_time(self):
        if time.time() - self.last_ntp_sync_time > self.ntp_sync_interval:
            self.sync_time_with_ntp()
        return time.time() + self.offset

    def get_read_value(self):
        try:
            value = self.pv.get()
            value = round(float(value), 5)
            return value
        except Exception as e:
            if self.verbose:
                print(f"Error reading value for {self.name}: {e}. \n {traceback.format_exc()}")
            return None

    def get_batch(self, n_samples=100) -> List[Dict[str, Any]]:
        return self.dataframe.iloc[-min(n_samples, len(self.dataframe)):]
    
    def get_single_value(self) -> Dict[str, Any]:
        current_time = self.get_time()
        scalar = self.get_read_value()
        #({'time': [current_time], 'value': [scalar]})
        return current_time, scalar

    def start_reading(self):
        print(f"Starting reading for {self.name}")
        if self.is_reading:
            if self.verbose:
                print("Reading is already in progress.")
            return
        self.is_reading = True
        self.reading_thread = threading.Thread(target=self._reading_loop, daemon=True)
        self.reading_thread.start()

    def _reading_loop(self):
        # t0 = self.get_time()
        while self.is_reading:
            try:
                current_time, current_wnum = self.get_single_value()
                if not current_time or not current_wnum:
                    if self.verbose:
                        print("Failed to get payload. Continuing.")
                    time.sleep(self.reading_frequency)
                    continue
                # if self.verbose:
                #     print(payload)

                self.update_plot_df(current_time, current_wnum)
                if self.saving_dir is not None:
                    self.save_single(current_time, current_wnum)
                    t0 = current_time  # Reset the saving time interval
                time.sleep(self.reading_frequency)
            except Exception as e:
                if self.verbose:
                    print(f"Exception in reading loop: {e}")

    def stop_reading(self):
        self.is_reading = False
        if self.reading_thread:
            self.reading_thread.join()

    def update_full_df(self, payload: List[Dict[str, Any]]):
        df = pd.DataFrame(payload)
        self.dataframe = pd.concat([self.dataframe, df], ignore_index=True)
    
    def update_plot_df(self, current_time, current_wnum):
        if len(self.xDat) == self.plot_limit:
            self.xDat = np.delete(self.xDat, 0)
            self.yDat = np.delete(self.yDat, 0)
        if len(self.xDat) == 0:
            self.xDat = np.array([0])
            self.first_time = self.get_time()
        else:
            rel_time = current_time - self.first_time
            self.xDat = np.append(self.xDat, rel_time)    
        self.yDat = np.append(self.yDat, current_wnum)       

    def save_full_df(self, dir):
        if not self.dataframe.empty:
            self.dataframe.to_csv(dir, mode='x', index=False)
            print(f"Data saved to {dir}")
    
    def save_single(self, time, wnum):
        if time and wnum:
            data = {'Time': [time],
                    'Wavenumber': [wnum]}
            table = pa.table(data)
            if os.path.exists(self.saving_dir):
                with open(self.saving_dir, 'ab') as f:
                    pc.write_csv(table, f, write_options=pc.WriteOptions(include_header=False))
            else:
                with open(self.saving_dir, 'wb') as f:
                    pc.write_csv(table, f, write_options=pc.WriteOptions(include_header=True))
            if self.verbose:
                print(f"Dava being saved to {self.saving_dir}")
    
    def clear_plot(self):
        self.xDat, self.yDat = np.array([]), np.array([])

    def get_latest_data(self) -> Optional[Dict[str, Any]]:
        return self.latest_data

    def get_dataframe(self) -> pd.DataFrame:
        return self.dataframe



class LaserControl(ControlLoop):
    def __init__(self, ip_address, port, wavenumber_pv):
        self.laser = None
        self.ip_address = ip_address
        self.port = port    
        self.patient_laser_init()
        self.wnum = 0.
        self.state = 0
        self.scan = 0
        # self.xDat = np.array([])
        # self.yDat = np.array([])
        # self.xDat_with_time = []
        # self.yDat_with_time = np.array([])
        self.target = 0.0
        self.scan_progress = 0.
        self.rate = 0.1  #in seconds
        self.conversion = 60
        self.now = datetime.datetime.now()
        self.pid = PIDController(kp=50., ki=0., kd=0., setpoint=self.target)######
        self.reader = EMAServerReader(pv_name=wavenumber_pv, reading_frequency=self.rate, saving_dir=None, verbose=True)
        #A list of commands to be sent to the laser 
        self.patient_setup_status()
        self.start_reading()
        self.set_current_wnum()

    def start_reading(self):
        self.reader.start_reading()
        
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
    
    def patient_update(self, tryouts = 2):
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
                if tries >= tryouts:
                    print(f"Unable to acquire laser information. Error: {e}")
                    raise ConnectionRefusedError
                else:
                    tries += 1

    def _update(self):
        self.set_current_wnum()
        #print(self.wnum)

        # if len(self.xDat) == 60:
        #     self.xDat = np.delete(self.xDat, 0)
        #     self.yDat = np.delete(self.yDat, 0)
        # if len(self.xDat) == 0:
        #     self.xDat = np.array([0])
        # else:
        #     self.xDat = np.append(self.xDat, self.xDat[-1] + self.rate*0.001)    

        # if len(self.xDat_with_time) == 0:
        #     self.xDat_with_time.append(self.now) 
        # else:
        #     self.xDat_with_time.append(self.xDat_with_time[-1] + self.time_converter(self.rate))
        
        # print(f"real: {datetime.datetime.now()}, stamp: {self.xDat_with_time[-1]}")

        # self.yDat = np.append(self.yDat, self.wnum)
        # self.yDat_with_time = np.append(self.yDat_with_time, self.wnum)

        if self.scan == 1:
            self._do_scan()

        if self.state == 1:
        #lock-in the wavelength of laser mode
            #print("locked")
            self.reference_cavity_tuner_value = self.laser.get_full_web_status()['cavity_tune']
            #set the wavelength to the target
            if self.init == 1:
                delta = self.target - self.wnum
                delta *= self.conversion
                self.laser.tune_reference_cavity(float(self.reference_cavity_tuner_value) - delta)
                self.init = 0
                self.pid.setpoint = self.target
                print("wavelength set")
            else:
                # Simple proportional control
                self.pid_filter_control(filter=False)
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

    def save_data(self, dir):
        self.reader.save_full_df(dir)

    def start_backup_saving(self, dir):
        self.reader.saving_dir = dir
    
    def stop_backup_saving(self):
        self.reader.saving_dir = None
    
    def get_df_to_plot(self):        
        # df_to_plot = self.reader.get_batch()
        # arrays = df_to_plot.to_numpy()
        # arrays = np.transpose(arrays)
        # ts = arrays[0, :]
        # ts = ts - ts[0]
        # wn = arrays[1, :]
        ts, wn = self.reader.xDat, self.reader.yDat
        df_to_plot = pd.DataFrame({"Wavenumber (cm^-1)": wn}, index = ts)
        return df_to_plot

    def set_current_wnum(self):
        self.wnum = self.reader.get_read_value()
    
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
                input_wnum = self.reader.get_read_value()
                i = round(i,0)    
                u = i * delta
                self.laser.tune_reference_cavity(float(self.reference_cavity_tuner_value) - u)                
                output_wnum = self.reader.get_read_value()
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
        rates = np.linspace(500, 1, 100)
        effective_rates = np.array([])
        loop = 0
        loop_end = 100
        while loop < loop_end:
            print(f"In {loop} loop now")
            for rate in rates:
                first = self.reader.get_read_value()
                time.sleep(rate*0.001)
                second = self.reader.get_read_value()
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

    def pid_filter_control(self, filter: bool):
        #print(f"pid.setpoint={self.pid.setpoint}")
        if filter:
            lower = self.target - 0.00002
            upper = self.target + 0.00002
            if self.wnum >= lower and self.current <= upper:
                pass
            else: 
                self._pid_control()
        else:
            self._pid_control()
    
    def _pid_control(self):
        u = self.pid.update(self.wnum)
        self.laser.tune_reference_cavity(float(self.reference_cavity_tuner_value) - u)

    def get_current_wnum(self):
        return self.wnum
    
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
                self.scan_time += round(self.rate, 5)
                #print(self.scan_time)
                #to convert rate to seconds
            print(f"progress:{self.scan_progress}")
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
        self.reader.clear_plot()
    
    def clear_dataset(self):
        self.reader.dataframe = pd.DataFrame(columns=['time', 'value'])
    
    def stop(self):
        self.reader.stop_reading()
        pass
