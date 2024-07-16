
import sys
import os
import time
import traceback
import numpy as np
sys.path.append('.\\src')
from control.st_laser_control import LaserControl

control_loop = LaserControl("192.168.1.222", 39933, "LaserLab:wavenumber_1")

#get conversion constant between wavenumber and cavity tuner percent value
# control_loop.get_conversion()
# control_loop.update()

control_loop.hack_reading_rate()

# list = np.linspace(100, 0, 20, dtype = int)
# print(list)