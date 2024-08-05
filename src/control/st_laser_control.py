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
    """PID controller that takes process variable and calculates the correction based on parameters and setpoint"""
    def __init__(self, kp, ki, kd, setpoint):
        """Constructor that specifies the p, i, d paramters and the setpoint

        Args:
            kp(float): proportional coefficient
            ki(float): intergal coefficient
            kd(float): derivative coefficient
            setpoint(float): setpoint for wavenumber
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.integral = 0
        self.previous_error = 0
        self.previous_time = time.time()
        self.first_update_call = True

    def update(self, current_value):
        """Calculates the correction
        
        Args:
            current_value(float): Process variable
        
        Returns:
            float: Error between the setpoint and process variable
            float: Correction
        """
        current_time = time.time()
        error = self.setpoint - current_value
        if self.first_update_call: 
            self.first_update_call = False
            derivative = 0.
        else:
            delta_time = current_time - self.previous_time
            self.integral += error * delta_time
            derivative = (error - self.previous_error) / delta_time

        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)

        self.previous_error = error
        self.previous_time = current_time

        return error, output
    
    def new_loop(self):
        """Reset everything for a new PID loop"""
        self.first_update_call = True
        self.integral = 0.
    
    def update_kp(self, new_value):
        """Update proportional gain
        
        Arg:
            new_value(float): New proportional constant
        """
        self.kp = new_value 

    def update_ki(self, new_value):
        """Update intergral gain
        
        Arg:
            new_value(float): New integral constant
        """
        self.ki = new_value 

    def update_kd(self, new_value):
        """Update proportional gain
            
            Arg:
                new_value(float): New proportional constant
            """
        self.kd = new_value 
    
    def update_setpoint(self, new_value):
        """Update the setpoint for PID controller
        
        Arg:
            new_value(float): New setpoint
        """
        self.setpoint = new_value



class EMAServerReader:
    """Server reader that creates a thread to get wavenumber from the server, synchronize time stamp with NTP server time, 
    and make data for saving and plotting"""
    def __init__(self, pv_name: str, reading_frequency: float = 0.1, ntp_sync_interval: float = 60, verbose: bool = False, plot_limit: int = 300, 
                 saving_interval: int = 30):
        """Constructor function that initializes the class.
        
        Args:
            pv_name(str): PV name for getting wavenumber
            reading_frequency(float): The frequency for reading data
            ntp_sync_interval(float): The interval to synchronize time stamp with NTP
            verbose(bool): Specifies whether to print message on the back end
            plot_limit(int): The number of points to be shown on the plot; plot_limit times reading_frequency gives the number of seconds to be plotted.
            saving_interval(int): The interval to save data to the disk
        """
        self.name = pv_name
        self.pv = PV(pv_name)
        self.saving_dir = None
        self.ntp_client = ntplib.NTPClient()
        self.timelist = []
        self.wnumlist = []
        self.saving_interval = saving_interval
        self.reading_frequency = reading_frequency
        self.ntp_sync_interval = ntp_sync_interval
        self.date_format = '%a %b %d %H:%M:%S %Y'
        self.verbose = verbose
        self.last_ntp_sync_time = time.time()
        self.offset = 0
        self.xDat = []
        self.yDat = []
        self.y_for_average = np.array([])
        self.first_time = 0.
        self.plot_limit = plot_limit
        self.reading_thread = None
        self.is_reading = False

    def sync_time_with_ntp(self):
        """Check the time offset between computer time and server time"""
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
        """Get time stamp based on server time and synchronize if reaching sync interval

        Returns:
            float: current time stamp based on server time
        """
        if time.time() - self.last_ntp_sync_time > self.ntp_sync_interval:
            self.sync_time_with_ntp()
        return time.time() + self.offset

    def get_read_value(self):
        """Get current wavenumber
        
        Return:
            float: current wavenumber rounded to 5 decimal places
        """
        try:
            value = self.pv.get()
            value = round(float(value), 5)
            return value
        except Exception as e:
            if self.verbose:
                print(f"Error reading value for {self.name}: {e}. \n {traceback.format_exc()}")
            return None
    
    def get_single_value(self):
        """Get single time stamp and wavenumber
        
        Returns:
            float: current server time
            float: current wavenumber
        """
        current_time = self.get_time()
        scalar = self.get_read_value()
        return current_time, scalar

    def start_reading(self):
        """Start a child thread for reading data"""
        if self.is_reading:
            if self.verbose:
                print("Reading is already in progress.")
            return
        else:
            if self.verbose:
                print(f"Starting reading for {self.name}")
            self.is_reading = True
            self.reading_thread = threading.Thread(target=self._reading_loop, daemon=True)
            self.reading_thread.start()

    def _reading_loop(self):
        """Loop to make the data for plotting and saving"""
        t0 = self.get_time()
        while self.is_reading:
            try:
                current_time, current_wnum = self.get_single_value()
                if not current_time or not current_wnum:
                    if self.verbose:
                        print("Failed to get payload. Continuing.")
                    time.sleep(self.reading_frequency)
                    continue
                # if self.verbose:
                #     print("Reading thread doing work")

                #self.update_plot_df(current_time, current_wnum)
                self.update_plot_df_no_average(current_time, current_wnum)
                if self.saving_dir is not None:
                    self.update_save_df(current_time, current_wnum)
                    if (current_time - t0) >= self.saving_interval:
                        self.save_full()
                        t0 = current_time  # Reset the saving time interval
                # if self.saving_dir is not None:
                #     self.save_single(current_time, current_wnum, 5)
                time.sleep(self.reading_frequency)
            except Exception as e:
                if self.verbose:
                    print(f"Exception in reading loop: {e}")

    def stop_reading(self):
        """Catch reading thread"""
        self.is_reading = False
        if self.reading_thread:
            self.reading_thread.join()
            self.reading_thread = None
            if self.verbose:
                print("Reading thread caught")

    def update_save_df(self, time, wnum):
        """Append last data to time and wavenumber list
        
        Args:
            time(float): time stamp
            wnum(float): wavenumber"""
        self.timelist.append(time)
        self.wnumlist.append(wnum)
    
    def update_plot_df(self, current_time, current_wnum, average_limit: int = 5):
        """Average the last average_limit wavenumbers, append the latest data to plotting lists and delete if they surpass the plotting limit
        
        Args:
            current_time(float): time stamp
            current_wnum(float): wavenumber
        """
        if len(self.xDat) == self.plot_limit:
            self.xDat.pop(0)
            self.yDat.pop(0)

        if len(self.xDat) == 0:
            self.first_time = self.get_time()
            self.xDat.append(0)
            self.yDat.append(current_wnum)
        
        if len(self.y_for_average) < average_limit:
            self.y_for_average = np.append(self.y_for_average, current_wnum)
        else:
            rel_time = current_time - self.first_time
            self.xDat.append(rel_time)
            mean = np.mean(self.y_for_average)
            self.yDat.append(mean)
            self.y_for_average = np.array([])
            self.y_for_average = np.append(self.y_for_average, current_wnum)

    def update_plot_df_no_average(self, current_time, current_wnum):
        """NO AVERAGE: Append the latest data to plotting lists and delete if they surpass the plotting limit

        Args:
            current_time(float): time stamp
            current_wnum(float): wavenumber
        """
        if len(self.xDat) == self.plot_limit:
            self.xDat.pop(0)
            self.yDat.pop(0)

        if len(self.xDat) == 0:
            self.first_time = self.get_time()
            self.xDat.append(0)
        else:
            rel_time = current_time - self.first_time
            self.xDat.append(rel_time)
        
        self.yDat.append(current_wnum)              
    
    def save_single(self, time, wnum):
        """Write the latest time to the disk.
        
        Args:
            current_time(float): time stamp
            current_wnum(float): wavenumber
        """
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
    
    def save_full(self):
        """Write data during the saving interval to the disk and clear cache"""
        data = {'Time': self.timelist,
                'Wavenumber': self.wnumlist}
        table = pa.table(data)
        if os.path.exists(self.saving_dir):
            with open(self.saving_dir, 'ab') as f:
                pc.write_csv(table, f, write_options=pc.WriteOptions(include_header=False))
        else:
            with open(self.saving_dir, 'wb') as f:
                pc.write_csv(table, f, write_options=pc.WriteOptions(include_header=True))
        self.timelist, self.wnumlist = [], []
        if self.verbose:
            print(f"Dava being saved to {self.saving_dir}")
    
    def get_plot_data(self):
        """Get data to Plot
        
        Returns:
            list: x data - time stamp
            list: y data - wavenumber
        """
        return self.xDat, self.yDat
    
    def clear_plot(self):
        """Clear the plot"""
        self.xDat, self.yDat = [], []



class LaserControl(ControlLoop):
    """Main class that controls the M2 laser"""
    def __init__(self, ip_address, port, wavenumber_pv, verbose):

        """Constructor function that initializes the class and passes laser information

        Args:
            ip_address(str): IP address for the M2 laser
            port(int): Port for the M2 laser
            wavenumber_pv(str): PV for getting wavenumber
            verbose(bool): whether to print messages on the terminal
        """
        self.laser = None
        self.ip_address = ip_address
        self.port = port    
        self.patient_laser_init()
        self.old_wnum = 0.
        self.wnum = 0.
        self.delta = 0.
        self.state = 0
        self.scan = 0
        self.target = 0.0
        self.scan_progress = 0.
        self.total_time = 0.
        self.scan_step_start_time = 0.
        self.current_pass = 0
        self.total_passes = 1
        self.rate = 0.1  #in seconds
        self.conversion = 60
        self.now = datetime.datetime.now()
        self.reply = None
        self.verbose = verbose
        self.update_tuner = 0
        self.tweaking_thread = None
        self.is_tweaking = False
        self.scan_restarted = False
        self.scan_start_time = 0.
        self.pid = PIDController(kp=40., ki=0.8, kd=0., setpoint=self.target)######
        self.reader = EMAServerReader(pv_name=wavenumber_pv, reading_frequency=self.rate, verbose=True)
        self.patient_setup_status()
        self.start_reading()
        self.set_current_wnum()

    def start_reading(self):
        """Start reading thread"""
        self.reader.start_reading()

    def stop_reading(self):
        """Stop reading thread"""
        self.reader.stop_reading()

    def patient_laser_init(self, tryouts = 2) -> None:
        """Try to instantiate the laser module
        
        Args:
            Tryouts(int): Times to try communicating with the M2 laser
        """
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
        """Initialize locks status and tuner value
        
        Arg:
            tryouts(int): Times to try to acquire laser information
        """
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

    def update(self):
        """Update funtion that runs every iteration, also an abstract method of the control loop"""
        self.set_current_wnum()
    
    def start_backup_saving(self, dir):
        """Passes the directory to the reader for data saving. This will automaticall start writing data to the disk"""
        self.reader.saving_dir = dir
    
    def stop_backup_saving(self):
        """Clear the saving directory of the reader, which will stop saving data automatically"""
        self.reader.saving_dir = None
    
    def get_df_to_plot(self):
        """Get data to plot from the reader
        Returns:
            list: x data - time stamp
            list: y data - wavenumber
        """        
        ts, wn = self.reader.get_plot_data()
        # if len(ts)>0 and len(wn)>0:
        #     print(ts[-1], wn[-1])
        # df_to_plot = pd.DataFrame({"Wavenumber (cm^-1)": wn}, index = ts)
        return ts, wn

    def set_current_wnum(self):
        """Set self.wnum to current wavenumber"""
        try:
            self.wnum = self.reader.get_read_value()
        except Exception as e:
            print(f"Error in setting the wavenumber: {e}")
            raise        
    
    def get_conversion(self):
        """Start process to hack the conversion constants between the wavenumber and voltage of the reference cavity"""
        self.state = 2
        self.start_tweaking()

    def do_conversion(self):
        """Try to hack the conversion constants between the wavenumber and voltage of the reference cavity"""
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
                self.tune_reference_cavity(float(self.reference_cavity_tuner_value) - u)
                #The use of tune_ref_cav is outdated here             
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
        """Hack the publishing rate of the wavemeter server"""
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

    def get_current_wnum(self):
        """Get the current wavenumber
        
        Return:
            float: current wavenumber
        """
        return self.wnum
    
    def lock(self, value):
        """Start a child thread to lock in the wavelength of the laser
        
        Arg:
            value(float): Target wavelength
        """
        self.state = 1
        if self.verbose:
            print(f"lock function called with state being {self.state}")
        self.target = value
        self.init = 1
        self.clear_plot()
        if self.tweaking_thread is None:
            self.start_tweaking()
            if self.verbose:
                print("One tweaking thread initiated for the wavelength lock")

    def unlock(self):
        """Unlock the wavelength of laser, clear the plot,  and stop the child thread"""
        self.state = 0
        self.scan = 0
        self.stop_tweaking()
        print("Unlock triggered")
        self.clear_plot()

    def lock_etalon(self):
        """Lock the etalon lock"""
        self.laser.lock_etalon()

    def unlock_etalon(self):
        """Unlock the etalon lock"""
        self.laser.unlock_etalon()

    def lock_reference_cavity(self):
        """Lock the reference cavity lock"""
        self.laser.lock_reference_cavity()

    def unlock_reference_cavity(self):
        """Unlock the reference cavity lock"""
        self.laser.unlock_reference_cavity()

    def tune_reference_cavity(self, value):
        """Tune reference cavity tuner to the set value
        
        Arg:
            value(float): Target tuner value for reference cavity tuner
        """
        if self.reply is None:
            self.reply = "something"
            self.reply = self.laser.tune_reference_cavity(value, sync=True)
            if self.verbose:
                print("ref cavity tuned")
        
    def tune_etalon(self, value):
        """Tune reference cavity tuner to the set value and acquire the latest etalon tuner value
        
        Arg:
            value(float): Target tuner value for reference cavity tuner
        """
        self.laser.tune_etalon(value)
        self.etalon_tuner_value = self.laser.get_full_web_status()['etalon_tune']
    
    def get_etalon_tuner(self):
        """Get current etalon tuner value
        
        Return:
            float: Current etalon tuner value"""
        return self.etalon_tuner_value

    def get_ref_cav_tuner(self, tryouts=2):
        """Get reference cavity tuner value

        Arg:
            tryouts(int): Times to try getting the cavity tuner value
        
        Return:
            float: Current ref cavity tuner value"""
        tries = 0
        for tries in range(tryouts):
            try:
                self.reference_cavity_tuner_value = float(self.laser.get_full_web_status()['cavity_tune'])
                break
            except Exception as e:
                print(f"Error in getting reference cavity tuner value: {e}")
                print(f"Tryouts: {tries}")
                if tries == 2:
                    raise ConnectionRefusedError
                tries += 1
                time.sleep(1)
        return self.reference_cavity_tuner_value
    
    def update_ref_cav_tuner(self):
        """Update the reference cavity tuner value asynchronously and return it
        Return:
            float: current reference cavity value
        """
        async def update_ref_tuner():
            try:
                before = self.reference_cavity_tuner_value
                value = await asyncio.get_event_loop().run_in_executor(None, self.get_ref_cav_tuner)
            except Exception as e:
                print(f"Error in updating reference cavity tuner value:{e}")
        
        asyncio.run(update_ref_tuner())
        return self.reference_cavity_tuner_value

    def update_etalon_lock_status(self):
        """Update the etalon lock status"""
        self.etalon_lock_status = self.laser.get_etalon_lock_status()

    def update_ref_cav_lock_status(self):
        """Update the reference cavity lock status"""        
        self.reference_cavity_lock_status = self.laser.get_reference_cavity_lock_status()

    def start_scan(self, start, end, no_scans, time_per_scan, no_of_passes):
        self.scan_targets = np.linspace(start, end, no_scans)
        self.set_tps = time_per_scan
        self.state = 1
        self.scan = 1
        self.j = 0
        self.jmax = no_scans
        self.scan_progress = 0.
        self.total_time = no_scans * time_per_scan
        self.total_passes = no_of_passes
        self.current_pass = 0
        self.scan_restarted = True
        self.start_tweaking()
    
    def stop_scan(self):
        self.scan = 0
        self.state = 0
        self.stop_tweaking()

    def end_scan(self):
        self.scan = 0
        self.state = 0
        self.scan_progress = self.total_time
        self.current_pass = 0
    
    def _do_scan(self):
        try:
            if self.scan_restarted:
                self.scan_time = self.set_tps
                self.scan_start_time = time.time()
                self.scan_restarted = False
            else:
                now = time.time()
                time_elapsed = now - self.scan_start_time
                time_elapsed_ps = now - self.scan_step_start_time
                self.scan_time = time_elapsed_ps
                self.scan_progress = time_elapsed
            if self.scan_time >= self.set_tps:
                if self.j < self.jmax:
                    self.target = self.scan_targets[self.j]
                    self.init = 1
                    #initialize, and one step forward
                    self.scan_time = 0
                    self.j += 1
                else: 
                    self.current_pass += 1
                    print(f"pass:{self.current_pass}")
                    if self.current_pass < self.total_passes:
                        self.scan_targets = np.flip(self.scan_targets)
                        self.j = 0
                        self.scan_progress = 0.
                        self.scan_restarted = True
                    else:
                        self.end_scan()
        except IndexError:
            self.scan = 0
            self.state = 0

    def scan_update(self, new_time_ps):
        self.set_tps = new_time_ps
    
    def wavelength_setter(self):
        delta = self.target - self.wnum #how much you would like to tune
        self.delta = delta
        delta *= self.conversion
        tuning = self.reference_cavity_tuner_value - delta
        self.tune_reference_cavity(tuning)
        print(f"setter tuning={delta}")
        self.reference_cavity_tuner_value = tuning
        self.init = 0
        self.pid.update_setpoint(self.target)
        #self.pid.setpoint = self.target
        self.pid.new_loop()
        if self.scan == 1:
            self.scan_step_start_time = time.time()
            if self.verbose:
                print(f"A new scan step starts at {self.scan_step_start_time}")
        if self.verbose:
            print("wavelength set")        
    
    def _pid_control(self):
        error, u = self.pid.update(self.wnum)
        #self.delta = error
        print(f"tuning={u}")
        tuning = float(self.reference_cavity_tuner_value) - u
        self.tune_reference_cavity(tuning)
        self.reference_cavity_tuner_value = tuning

    def pid_filter_control(self, filter: bool):
        #If filter set to True, then a 1MHZ window for the PID control will be enabled.
        if filter:
            lower = self.target - 0.00002
            upper = self.target + 0.00002
            if self.wnum >= lower and self.wnum <= upper:
                self.pid.new_loop()
            else: 
                self._pid_control()
        else:
            self._pid_control()
    
    def p_update(self, value):
        try:
            self.pid.update_kp(float(value))
        except ValueError:
            raise

    def i_update(self, value):
        try:
            self.pid.update_ki(float(value))
        except ValueError:
            raise
    
    def d_update(self, value):
        try:
            self.pid.update_kd(float(value))
        except ValueError:
            raise
    
    def start_tweaking(self):
        print(f"Starting tweaking {self.laser}")
        if self.is_tweaking:
            if self.verbose:
                print("Tweaking is already in progress")
            return
        self.is_tweaking = True
        self.tweaking_thread = threading.Thread(target=self._tweaking_loop, daemon=True)
        self.tweaking_thread.start()

    def update_conversion(self):
        conversion_change = 1
        self.old_wnum = self.wnum
        self.set_current_wnum()        
        actual_delta = self.wnum - self.old_wnum
        if abs(actual_delta) < abs(self.delta): self.conversion += conversion_change
        elif abs(actual_delta) > abs(self.delta): self.conversion -= conversion_change
        else: pass
        if self.conversion > 90:
            raise ValueError           
        print(f"conversion updated to {self.conversion}")

    def _tweaking_loop(self):
        # t0 = self.get_time()
        while self.is_tweaking:
            for t in range(4):
                try:
                    self.set_current_wnum()

                    self.update_tuner += 1
                    if self.update_tuner == 5:
                        before = self.reference_cavity_tuner_value
                        now = self.update_ref_cav_tuner()
                        self.update_tuner = 0
                        print(f"Ref cav updated from {before} to {now}")

                    if self.scan == 1:
                        self._do_scan()

                    if self.state == 1:
                    #lock-in the wavelength of laser mode
                        #print("locked")
                        #set the wavelength to the target
                        if self.init == 1:
                            self.wavelength_setter()
                            self.update_conversion()
                        else:
                            # Simple proportional control
                            self.pid_filter_control(filter=True)
                            # print(f"target:{self.target}")
                            # print(f"current:{self.wnum}")
                            # print(f"correction:{u}")
                            # print("wavelength in control")
                    
                    if self.state == 2:
                    #get conversion constant mode
                        self.do_conversion()
                    # if self.verbose:
                    #     print("Tweaking loop in progress")
                    time.sleep(0.1)
                    break
                except Exception as e:
                    if self.verbose:
                        print(f"{t}th trial. Exception in tweaking the laser: {e}")
                    if t == 3:
                        raise ConnectionRefusedError
                    time.sleep(1)

    def stop_tweaking(self):
        self.is_tweaking = False
        if self.tweaking_thread:
            self.tweaking_thread.join()
            self.tweaking_thread = None
            if self.verbose:
                print("Tweaking thread caught")

    def time_converter(self, value):
        return datetime.timedelta(milliseconds = value)

    def clear_plot(self):
        """Clear the data to plot"""
        self.reader.clear_plot()
    
    def stop(self):
        """Stop all child threads"""
        self.reader.stop_reading()
        self.stop_tweaking()
        pass
