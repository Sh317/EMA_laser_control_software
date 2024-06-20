from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from .base import GUI
import numpy as np
import os

path2file = os.path.join(os.path.dirname(__file__))


class LaserGUI(QWidget):
    def __init__(self, control_loop, parent=None):
        super(LaserGUI, self).__init__()
        self.control_loop = control_loop
        self.control_loop.gui_callback = self.update_display
        self.setup_ui()
        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.control_loop.update)
        self.timer.start()

    def setup_ui(self):
        self.wl = QDoubleSpinBox()
        self.wl.setDecimals(5)
        self.wl.setMaximum(99999.99999)
        self.wl.setStepType(QAbstractSpinBox.AdaptiveDecimalStepType)
        self.wl.setValue(round(float(self.control_loop.wavenumber.get()), 5))

        self.startwl = QDoubleSpinBox()
        self.startwl.setDecimals(5)
        self.startwl.setMaximum(99999.99999)
        self.startwl.setStepType(QAbstractSpinBox.AdaptiveDecimalStepType)
        self.startwl.setValue(round(float(self.control_loop.wavenumber.get()), 5))

        self.endwl = QDoubleSpinBox()
        self.endwl.setDecimals(5)
        self.endwl.setMaximum(99999.99999)
        self.endwl.setStepType(QAbstractSpinBox.AdaptiveDecimalStepType)
        self.endwl.setValue(round(float(self.control_loop.wavenumber.get()), 5))

        self.no_scans = QDoubleSpinBox()
        self.no_scans.setDecimals(0)
        self.no_scans.setMaximum(50)
        self.no_scans.setValue(5)

        self.tps = QDoubleSpinBox()
        self.tps.setDecimals(1)
        self.tps.setMaximum(50)
        self.tps.setStepType(QAbstractSpinBox.AdaptiveDecimalStepType)
        self.tps.setValue(2)

        self.pc = QDoubleSpinBox()
        self.pc.setDecimals(2)
        self.pc.setMaximum(9.99)
        self.pc.setStepType(QAbstractSpinBox.AdaptiveDecimalStepType)
        self.pc.setValue(4.5)
        self.pc.valueChanged.connect(self.control_loop.p_update)

        self.lb = QPushButton()
        self.lb.setObjectName("lock")
        self.lb.setText("Lock")
        self.lb.setCheckable(True)
        self.lb.clicked.connect(self.lock)

        self.ulb = QPushButton()
        self.ulb.setObjectName("unlock")
        self.ulb.setText("Unlock")
        self.ulb.clicked.connect(self.unlock)

        self.scanb = QPushButton()
        self.scanb.setObjectName("Start Scan")
        self.scanb.setText("Start Scan")
        self.scanb.clicked.connect(self.start_scan)

        layout = QHBoxLayout()
        layout.addWidget(self.wl)
        layout.addWidget(self.lb)
        layout.addWidget(self.ulb)

        self.p_label = QLabel()
        self.p_label.setText("P Constant:")

        layout_2 = QHBoxLayout()
        layout_2.addWidget(self.p_label)
        layout_2.addWidget(self.pc)

        self.start_label = QLabel()
        self.end_label = QLabel()
        self.num_label = QLabel()
        self.time_label = QLabel()

        self.start_label.setText("Start wavelength:")
        self.end_label.setText("End wavelength:")
        self.num_label.setText("No. scans:")
        self.time_label.setText("Time per scan (seconds):")

        layout_3 = QHBoxLayout()
        layout_3.addWidget(self.start_label)
        layout_3.addWidget(self.startwl)
        layout_3.addWidget(self.end_label)
        layout_3.addWidget(self.endwl)
        layout_3.addWidget(self.num_label)
        layout_3.addWidget(self.no_scans)
        layout_3.addWidget(self.time_label)
        layout_3.addWidget(self.tps)
        layout_3.addWidget(self.scanb)

        layout_4 = QHBoxLayout()
        self.etalock = QLabel()
        self.etalock.setText("Etalon Lock:")
        self.etalocklock = QLabel()
        self.etalocklock.setPixmap(
            QPixmap(os.path.join(path2file, "locked.jpg")).scaledToWidth(32)
        )
        self.cavlock = QLabel()
        self.cavlock.setText("Cavity Lock:")
        self.cavlocklock = QLabel()
        self.cavlocklock.setPixmap(
            QPixmap(os.path.join(path2file, "locked.jpg")).scaledToWidth(32)
        )
        self.plotWidget = pg.PlotWidget()

        self.cwl = QLabel()
        self.cwl.setText(str(round(float(self.control_loop.wavenumber.get()), 5)))
        layout_4.addWidget(self.cwl)
        layout_4.addWidget(self.etalock)
        layout_4.addWidget(self.etalocklock)
        layout_4.addWidget(self.cavlock)
        layout_4.addWidget(self.cavlocklock)

        flo = QFormLayout()
        flo.addRow("Current Wavelength:", layout_4)
        flo.addRow("Target Wavelength:", layout)
        flo.addRow("", layout_2)
        flo.addRow("", layout_3)
        flo.addRow("Plot", self.plotWidget)
        self.setLayout(flo)
        self.setWindowTitle("UROP")

    def lock(self):
        if self.lb.isChecked():
            self.control_loop.lock()
            self.lb.setChecked(True)

    def unlock(self):
        self.control_loop.unlock()
        if self.lb.isChecked():
            self.lb.setChecked(False)

    def start_scan(self):
        start = self.startwl.value()
        end = self.endwl.value()
        no_scans = int(self.no_scans.value())
        time_per_scan = self.tps.value()
        self.control_loop.start_scan(start, end, no_scans, time_per_scan)

    def closeEvent(self, event):
        self.control_loop.stop()
        event.accept()

    def update_display(self, wnum, x_data, y_data):
        print(f"Update display called with wnum: {wnum}")
        self.cwl.setText(str(wnum))
        self.plotWidget.plot(x_data, y_data, clear=True)
