import pyarrow as pa
import pyarrow.csv as pc
import os
import ntplib
import time
from epics import PV
import numpy as np
from typing import List, Dict, Any, Optional
import threading
import asyncio
import traceback

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

    def get_last_plot_data(self):
        """Get the last data point for Plot
        
        Returns:
            list: x data - time stamp
            list: y data - wavenumber
        """
        if self.xDat and self.yDat:
            return self.xDat[-1], self.yDat[-1]
        else:
            if self.verbose:
                print("No data to plot.")
            return None, None
    
    def clear_plot(self):
        """Clear the plot"""
        self.xDat, self.yDat = [], []
