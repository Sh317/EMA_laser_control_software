import sys
from PyQt5.QtWidgets import QApplication
sys.path.append('.\\src')
from control.old_laser_control import LaserControl
from ui.old_gui import LaserGUI

if __name__ == '__main__':
    app = QApplication(sys.argv)
    control_loop = LaserControl("192.168.1.222", 39933, "LaserLab:wavenumber_1")
    form = LaserGUI(control_loop)
    app.aboutToQuit.connect(form.closeEvent)
    form.show()
    sys.exit(app.exec_())
