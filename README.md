# Laser Control and GUI Application

## Overview

This project provides a modular application for controlling a laser system and visualizing its operations using a graphical user interface (GUI).

## Directory Structure

```
project/
│
├── control_loop.py
├── laser_control.py
├── gui_base.py
├── laser_gui.py
├── run.py
└── resources/
    ├── locked.jpg
    └── unlocked.jpg
```

### Files and Their Roles

- **control_loop.py**: Contains the abstract base class for the control loop.
- **laser_control.py**: Implements the control loop specific to the laser system.
- **gui_base.py**: Contains the abstract base class for the GUI.
- **laser_gui.py**: Implements the GUI for the laser control.
- **run.py**: Script to launch the GUI application.
- **resources/**: Directory containing image resources used in the GUI (e.g., lock/unlock icons).

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

This file implements the `ControlLoop` class specifically for the laser system:

- Connects to the laser using the `M2.Solstis` class.
- Manages the wavenumber using EPICS PV.
- Implements methods to update the laser state, lock/unlock the laser, start a scan, and stop the control loop.

### GUI

#### `gui_base.py`

This file defines an abstract base class `GUI` with the following method:

- `setup_ui()`: Abstract method to set up the user interface.

#### `laser_gui.py`

This file implements the `GUI` class for the laser control application:

- Creates a GUI using PyQt5.
- Provides input fields for setting wavelength, scan parameters, and a P constant.
- Displays the current wavelength and lock status.
- Visualizes the laser's operation using a plot widget.
- Connects to the control loop to update and manage the laser state.

### Running the Application

#### `run.py`

This file launches the GUI application:

- Initializes the QApplication.
- Creates an instance of `LaserControl`.
- Passes the control loop to the `LaserGUI`.
- Starts the Qt event loop.

## How to Use

1. **Ensure Dependencies are Installed**:
   - PyQt5
   - pyqtgraph
   - epics
   - numpy
   - pylablib

   You can install these dependencies using pip:
   ```bash
   pip install PyQt5 pyqtgraph epics numpy pylablib
   ```

2. **Run the Application**:
   Execute the `run.py` script to launch the GUI:
   ```bash
   python scripts/run.py
   ```

3. **Using the GUI**:
   - **Locking/Unlocking the Laser**: Use the "Lock" and "Unlock" buttons.
   - **Setting Wavelength**: Adjust the wavelength using the provided spin boxes.
   - **Starting a Scan**: Set the scan parameters and click "Start Scan".
   - **Visualizing Data**: The GUI will display the current wavelength and lock status, and plot the laser's operation.

## Contributors

- Johanse
- Sherlock
- Jose M

EMA LAB,
MIT
