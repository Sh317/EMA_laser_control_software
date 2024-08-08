# Laser Control and GUI Application

## Overview

This project provides a modular application for controlling a laser system and visualizing its operations using a graphical user interface (GUI).

## Directory Structure

```
project/
│
├── control_loop.py
├── st_laser_control.py
├── pid_controller.py
├── server_reader.py
├── st_ui.py
├── get_info.py

```

### Files and Their Roles

- **control_loop.py**: Contains the abstract base class for the control loop
- **st_laser_control.py**: Implements the control loop specific to the laser system
- **pid_controller.py**: Contains a class for PID feedback control system
- **server_reader.py**: Contains a class for reading data from the EMA lab server
- **st_ui.py**: Implements the GUI for the laser control
- **get_info.py**: Script to hack information of the laser, including the reading rate and conversion constant

## Components

### Control Loop

#### `control_loop.py`

This file defines an abstract base class `ControlLoop` with the following methods:

- `update()`: Abstract method to update the control loop.
- `lock()`: Abstract method to lock the laser.
- `unlock()`: Abstract method to unlock the laser.
- `start_scan(start, end, no_scans, time_per_scan)`: Abstract method to start a scan.
- `stop()`: Abstract method to stop the control loop.

#### `laser_control.py`

This file implements `PIDController` and `EMAServerReader` for feedback control, reading data, and timing and implements the `ControlLoop` class specifically for the laser system:

- Connects to the laser using the `M2.Solstis` class.
- Manages the wavenumber using EPICS PV.
- Implements methods to update the laser state, lock/unlock the laser, start a scan, and stop the control loop.

#### `pid_controller.py`

This file defines a Proportional-Integral-Derivative (PID) control algorithm to adjust a process variable to match a desired setpoint:

- Configures the PID parameters (kp, ki, kd) and the setpoint. 
- Calculates error and correction based on the current process variable.

#### `ema_server_reader.py`

This file defines the EMAServerReader class for reading and synchronizing wavenumber data from a server:

- Connects to a PV to read the wavenumber at a specified frequency.
- Synchronizes timestamps with an NTP server at defined intervals.
- Provides methods to start/stop reading in a separate thread.
- Updates and maintains data for plotting and saving.
- Saves data to disk at regular intervals.

### GUI

#### `st_ui.py`

This file implements the `GUI` class for the laser control application:

- Creates a GUI that includes main page and four tabs using streamlit.
- Main page includes visualization of the laser's operation using a plot widget and display of current wavelength and reading rate.
- Tab1 provides functionality to interact with laser settings, input fields for locking in wavelength, and settings for PID control system. 
- Tab2 offers input fields for scan settings and displays an overview and status of the scan.
- Tab3 includes settings for saving data.
- Tab4 displays status of different threads options to stop them.
- Connects to the control loop to update and manage the laser state.

## How to Use

1. **Ensure Dependencies are Installed**:
   - Streamlit
   - plotly
   - epics
   - numpy
   - pylablib
   - pyarrow
   - wx

   You can install these dependencies using pip:
   ```bash
   pip install Streamlit plotly epics numpy pylablib pyarrow wx
   ```

2. **Run the Application**:
   Clone this repo and the run with:
   ```bash
   streamlit run ./src/ui_st/st_ui.py
   ```

3. **Using the GUI**:
   - **Locking/Unlocking the Laser**: Use the "Lock" and "Unlock" buttons.
   - **Setting Wavelength**: Adjust the wavelength using the provided number input.
   - **Starting a Scan**: Set the scan parameters and click "Start Scan".
   - **Visualizing Data**: The GUI will display the current wavelength and lock status, and plot the laser's operation.

## Caveats
1. **Streamlit default refresh**: Adjusting the input in most widgets would trigger an automatic rerun of the code, which may take a few seconds if it's trying to communicate with hardwares.
2. **Streamlit session state**: Most settings of the softwareare stored in memory through streamlit session state. That means if the software is re-initiated(refreshing the page through browser), all status displayed will be reset. *Please always check the threading status after refreshing the page. In default, only reading thread will be on duty.* 

## Debugs
1. **Lock status not up-to-date**: This is due the streamlit session state settings (see Caveats). When the software is initiated and changes are done through other ends like M2 software, such changes won't be updated on the UI. To solve it, try refresh the whole page(not click "rerun"), which will reset the session state.
3. **Wavelength lock and scanning**: When wavelength lock and scanning are not working as expected, please double check the terminal and M2 software. Possibilies include the software was not able to acquire the correct refrence cavity tuner value and the M2 laser has been tweaked too much and it's recovering to the set wavelength.
4. **Backend error: Socket Timeout**: If such error occured, please try to refresh the page and rerun the code.
5. **Unexpected lock status**: These errors were rasied because the software was not able to reach the server. Please make sure the computer is connected to EMA_LAB and the server is running.

## Contributors

- Johanse
- Sherlock Z 
- Jose M

EMA LAB,
MIT
