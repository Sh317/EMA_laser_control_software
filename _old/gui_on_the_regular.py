from pylablib.devices import M2
import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from epics import PV
import pyqtgraph as pg
import numpy as np

import platform
import ctypes

if platform.system()=='Windows' and int(platform.release()) >= 8:  #prevents axis misalignment when going between monitors
    ctypes.windll.shcore.SetProcessDpiAwareness(True) #https://stackoverflow.com/questions/69140610/pyqtgraph-when-show-in-a-different-screen-misalign-axis

laser = M2.Solstis("192.168.1.222", 39933)
wavenumber = PV("LaserLab:wavenumber_3")

class Form(QWidget):
    def __init__(self, parent=None):
        super(Form, self).__init__(parent)
        self.state = 0
        self.scan = 0  

        step_type = QAbstractSpinBox.AdaptiveDecimalStepType
        
        self.wl = QDoubleSpinBox()
        self.wl.setDecimals(5)
        self.wl.setMaximum(99999.99999)
        self.wl.setStepType(step_type)
        self.wl.setValue(round(float(wavenumber.get()),5))

        self.startwl = QDoubleSpinBox()
        self.startwl.setDecimals(5)
        self.startwl.setMaximum(99999.99999)
        self.startwl.setStepType(step_type)
        self.startwl.setValue(round(float(wavenumber.get()),5))

        self.endwl = QDoubleSpinBox()
        self.endwl.setDecimals(5)
        self.endwl.setMaximum(99999.99999)
        self.endwl.setStepType(step_type)
        self.endwl.setValue(round(float(wavenumber.get()),5))

        self.no_scans = QDoubleSpinBox()
        self.no_scans.setDecimals(0)
        self.no_scans.setMaximum(50)
        self.no_scans.setValue(5)
        
        self.tps = QDoubleSpinBox()
        self.tps.setDecimals(1)
        self.tps.setMaximum(50)
        self.tps.setStepType(step_type)
        self.tps.setValue(2)
            
        self.pc = QDoubleSpinBox()
        self.pc.setDecimals(2)
        self.pc.setMaximum(9.99)
        self.pc.setStepType(step_type)
        self.pc.setValue(4.5)
        self.p = 4.5
        self.pc.valueChanged.connect(self.p_update)
        
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
        self.etalocklock.setPixmap(QPixmap("locked.jpg").scaledToWidth(32))
        self.cavlock = QLabel()
        self.cavlock.setText("Cavity Lock:")
        self.cavlocklock = QLabel()
        self.cavlocklock.setPixmap(QPixmap("locked.jpg").scaledToWidth(32))
        
        self.plotWidget = pg.PlotWidget() #create plot widget, add to horizontal layout   
        
        self.wnum = round(float(wavenumber.get()),5)
        self.target = 0.0
        self.cwl = QLabel()
        self.cwl.setText(str(self.wnum))
        layout_4.addWidget(self.cwl)
        layout_4.addWidget(self.etalock)
        layout_4.addWidget(self.etalocklock)
        layout_4.addWidget(self.cavlock)
        layout_4.addWidget(self.cavlocklock)
        
        flo = QFormLayout()
        flo.addRow("Current Wavelength:", layout_4)
        flo.addRow("Target Wavelength:", layout)
        flo.addRow("",layout_2)
        flo.addRow("",layout_3)
        flo.addRow("Plot", self.plotWidget)
        self.setLayout(flo)
        self.timer = QTimer() 
        self.timer.setInterval(100) 
        self.timer.timeout.connect(self.update)
        self.timer.start()
        self.setWindowTitle("UROP")
        
        self.xDat = np.array([])
        self.yDat = np.array([])
        
    def update(self):
        self.wnum = round(float(wavenumber.get()),5)
        #print(self.wnum)
        self.cwl.setText(str(self.wnum))
        etalon_lock_status = laser.get_etalon_lock_status()
        reference_cavity_lock_status = laser.get_reference_cavity_lock_status()
        if etalon_lock_status == 'off':
            self.etalocklock.setPixmap(QPixmap("unlocked.jpg").scaledToWidth(32))
        else:
            self.etalocklock.setPixmap(QPixmap("locked.jpg").scaledToWidth(32))

        if reference_cavity_lock_status == 'off':
            self.cavlocklock.setPixmap(QPixmap("unlocked.jpg").scaledToWidth(32))
        else:
            self.cavlocklock.setPixmap(QPixmap("locked.jpg").scaledToWidth(32))
            
        if self.state == 1:
            if etalon_lock_status == 'off' or reference_cavity_lock_status == 'off':
                self.unlock()
                print("Something is Unlocked")
            try:
                if len(self.xDat) == 60:
                    self.xDat = np.delete(self.xDat, 0)
                    self.yDat = np.delete(self.yDat, 0)
                
                self.xDat = np.append(self.xDat,self.xDat[-1] + 100)
                self.yDat = np.append(self.yDat,self.wnum)
            except:
                self.xDat = np.array([100])
                self.yDat = np.array([self.wnum])
            delta = self.target - self.wnum    
            self.plotLine.setData(self.xDat,self.yDat)
            u = self.p * delta 
            cavity = laser.get_full_status(include = ['web_status'])['web_status']['cavity_tune']
            laser.tune_reference_cavity(float(cavity) - u)
            #print(self.tot)
            
        if self.scan == 1:
            if abs(delta) <= 0.00005 and not self.do_time:
                self.do_time = 1
                #print('yo')

            if self.do_time:
                self.scan_time = self.scan_time + 100
            if self.scan_time == self.time_ps:
                self.j += 1
                self.scan_time = 0
                try:
                    self.target = self.scan_targets[self.j]
                    self.plotWidget.addLine(x=None, y=self.target, pen='blue')
                    self.do_time = 0
                except:
                    print("scan complete")
                    self.scan = 0
                    self.state = 0
                    self.lb.toggle()
                
            
    def lock(self):
      if self.lb.isChecked():
         print ("Locked")
         self.state = 1
         self.target = self.wl.value()
         self.plotWidget.clear()
         self.plotLine=self.plotWidget.plot(pen='red')
         self.plotWidget.addLine(x=None, y=self.target, pen='blue')
         
      else:
         self.lb.toggle()

    def start_scan(self):
        if not self.lb.isChecked():
            start = self.startwl.value()
            end = self.endwl.value()
            no_steps = int(self.no_scans.value())
            self.scan_targets = np.linspace(start, end, no_steps)
            #print(self.scan_targets)
            self.time_ps = self.tps.value() * 1000
            self.target = self.scan_targets[0]
            self.state = 1
            self.scan = 1
            self.do_time = 0
            self.scan_time = 0
            self.j = 0
            self.plotWidget.clear()
            self.plotLine=self.plotWidget.plot(pen='red')
            self.plotWidget.addLine(x=None, y=self.target, pen='blue')
            self.lb.toggle()

    def unlock(self):
        if self.lb.isChecked():
            self.lb.toggle()
            self.state = 0
            self.scan = 0
            self.xDat = np.array([])
            self.yDat = np.array([])
            print("Unlocked")

    def stop(self):
        self.timer.stop()

    def p_update(self,swag):
        try:
            self.p = float(swag)
        except:
            self.p = 0
            


app = QApplication(sys.argv)

form = Form()
app.aboutToQuit.connect(form.stop)
form.show()
app.exec_()


