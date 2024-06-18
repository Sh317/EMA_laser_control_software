from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg
import numpy as np
import sys

import platform
import ctypes
if platform.system()=='Windows' and int(platform.release()) >= 8:  #prevents axis misalignment when going between monitors
  ctypes.windll.shcore.SetProcessDpiAwareness(True) #https://stackoverflow.com/questions/69140610/pyqtgraph-when-show-in-a-different-screen-misalign-axis

class livePlotTemplateGUI(QtWidgets.QMainWindow):
  def __init__(self):
    super().__init__()
    self.setWindowTitle('this is where you set the window title')
    self.cw=QtWidgets.QWidget(); self.setCentralWidget(self.cw) #create empty widget and set it as central widget
    self.horizontalLayout = QtWidgets.QHBoxLayout(); self.cw.setLayout(self.horizontalLayout) #create horizontal layout, and set central widget to use this layout. This will hold everything

    '''Setting up the plot'''
    self.plotWidget = pg.PlotWidget(); self.horizontalLayout.addWidget(self.plotWidget) #create plot widget, add to horizontal layout
    self.plotLine=self.plotWidget.plot(pen='red') #this instantiates an empty line object

    '''Adding buttons and such'''
    self.verticalLayout = QtWidgets.QVBoxLayout(); self.horizontalLayout.addLayout(self.verticalLayout) #create vertical layout, and add it to horizontal layout. This is where I'll put other widgets
    self.meanLabel = QtWidgets.QLabel('mean value:'); self.verticalLayout.addWidget(self.meanLabel) #a label widget which we'll update
    self.scaleSpinBox = QtWidgets.QDoubleSpinBox(value=1, minimum=0,maximum=100,singleStep=0.1); self.verticalLayout.addWidget(self.scaleSpinBox)

    self.currentlyLive=True #simple way to toggle the plotting. I think it would be better form to start/stop the thread, but I'm doing it like this for simplicity of example
    self.startButton = QtWidgets.QPushButton('stop'); self.verticalLayout.addWidget(self.startButton) #a button to start and stop live plotting
    self.startButton.clicked.connect(self.toggleUpdates) #widgets have 'signals'. When the 'clicked' signal is emmitted upon clicking the button, we connect it to our toggle Update Function

    '''creating thread for live-plotting'''
    self.timer = QtCore.QTimer() #As I understand it, the timer object is basically QT's built-in version of creating a new thread
    self.timer.setInterval(50) #update interval is measured in ms
    self.timer.timeout.connect(self.updateFunction)
    self.timer.start()

  def toggleUpdates(self): #this is what gets called whenever we click the button
    self.currentlyLive=not(self.currentlyLive)
    self.startButton.setText('stop') if self.currentlyLive else self.startButton.setText('start')

  def updateFunction(self):
    #every update interval, this function is called, and self.plotLine is updated to a new set of data
    if self.currentlyLive:
      xDat=np.linspace(0,99,100)
      yDataScale=self.scaleSpinBox.value() #kinda hacky but it works. Could also 
      yDat=yDataScale*np.random.random(100)
      self.plotLine.setData(xDat,yDat)
      self.latestMean=np.mean(yDat)
      self.meanLabel.setText('mean: %.3f'%np.mean(yDat))
  
  def safeExit(self):
    #this is how you can ensure that everything shuts down/is recorded properly even if someone closes the window unexpectedly. Remember to connect it to the QApplication in main
    print("you closed the app. Here's the last mean recorded:", self.latestMean)

if __name__ == '__main__':
  app = QtWidgets.QApplication(sys.argv)
  window = livePlotTemplateGUI()
  
  app.aboutToQuit.connect(window.safeExit)
  window.show()
  sys.exit(app.exec_())
