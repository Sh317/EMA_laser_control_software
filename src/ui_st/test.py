import time
import numpy as np
import pandas as pd
import ntplib
from epics import PV
from time import ctime
from typing import List, Dict, Any, Optional
import threading
import asyncio
import warnings
# with warnings.catch_warnings():
#     warnings.simplefilter("ignore")
#     from CaChannel.util import caget

class EMAServerReader:
    def __init__(self, pv_name: str, saving_dir: str = None, reading_frequency: float = 0.01,
                 write_each: float = 100, ntp_sync_interval: float = 60, verbose: bool = False):
        # self.name = pv_name
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
                print(f"Error reading value for {self.name}: {e}")
            return None

    def get_batch(self, n_samples=100) -> List[Dict[str, Any]]:
        return self.dataframe.iloc[-min(n_samples, len(self.dataframe)):]
    
    
    def get_single_value(self) -> Dict[str, Any]:
        current_time = self.get_time()
        scalar = self.get_read_value()
        return {'time': [current_time], 'value': [scalar]}

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
        t0 = self.get_time()
        while self.is_reading:
            try:
                payload = self.get_single_value()
                if not payload:
                    if self.verbose:
                        print("Failed to get payload. Continuing.")
                    time.sleep(self.reading_frequency)
                    continue
                current_time = payload['time']
                # if self.verbose:
                #     print(payload)

                self.update_df(payload)
                if self.saving_dir is not None and (current_time - t0) >= self.saving_interval:
                    self.save_df()
                    t0 = current_time  # Reset the saving time interval
                time.sleep(self.reading_frequency)
            except Exception as e:
                if self.verbose:
                    print(f"Exception in reading loop: {e}")

    def stop_reading(self):
        self.is_reading = False
        if self.reading_thread:
            self.reading_thread.join()

    def update_df(self, payload: List[Dict[str, Any]]):
        df = pd.DataFrame(payload)
        self.dataframe = pd.concat([self.dataframe, df], ignore_index=True)

    def save_df(self):
        if not self.dataframe.empty:
            self.dataframe.to_csv(self.saving_dir, index=False)
            if self.verbose:
                print(f"Data saved to {self.saving_dir}")

    def get_latest_data(self) -> Optional[Dict[str, Any]]:
        return self.latest_data

    def get_data_frame(self) -> pd.DataFrame:
        return self.dataframe


# Example usage
if __name__ == '__main__':
    reader = EMAServerReader('LaserLab:wavenumber_1', saving_dir=None, verbose=True)
    reader.start_reading()
    while True:
        try:
            print(reader.get_read_value())
            time.sleep(0.01)
        except Exception as e:
            print(f"error:{e}")
            break
