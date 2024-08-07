from PyQt5 import QtCore
from PyQt5.QtWidgets import QPushButton
import pyqtgraph as pg
import time
import serial
import datetime

class arduino_telemetry():
    def __init__(self, window, initparams):
        self.window = window

        self.ser = serial.Serial(
            port='/dev/ttyUSB0',
            baudrate=9600,
            parity=serial.PARITY_ODD,
            stopbits=serial.STOPBITS_TWO,
            bytesize=serial.SEVENBITS
        )
        self.my_telem_plots = []
        for telem_plot in initparams["plots"]:
            self.my_telem_plots.append(arduino_plot(self.window, telem_plot))

        self.serialchecker = QtCore.QTimer()
        self.serialchecker.timeout.connect(self.check_serial)
        self.serialchecker.start(50)
        self.check_serial()
            
    def check_serial(self):
        if(self.ser.inWaiting()):
            pkt = self.ser.readline()
            if pkt[:2] == b"aX":
                xval = pkt[6:11].decode('utf-8').strip()
                yval = pkt[20:25].decode('utf-8').strip()
                zval = pkt[34:40].decode('utf-8').strip()
                t = datetime.datetime.now()
                self.my_telem_plots[0].update_graph(t, int(xval))
                self.my_telem_plots[1].update_graph(t, int(yval))
                self.my_telem_plots[2].update_graph(t, int(zval))

class arduino_plot():
    def __init__(self,window,initparams):
        #Iterate over everything in initparams.
        for key,value in initparams.items():
            #This does self.key = value, where key is a string.
            setattr(self, key, value)
        self.window = window
        self.box = pg.GraphicsLayoutWidget(window)
        self.window.grid.addWidget(self.box, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
        self.box.setStyleSheet("border:2px solid black; border-radius: 5px;")

        self.dataplot = self.box.addPlot(title = self.name,labels = {'bottom':"Time (sec)","left":self.ylabel})
        self.dataplot.setRange(xRange=[-self.x_timerange, 0.2])
        self.plotline = self.dataplot.plot()
        self.minsize = 0
        self.xvals = []
        self.yvals = []

        #Expansion button to make the main widget thing
        self.mainwidgetbutton = QPushButton("⛶",self.box)
        self.mainwidgetbutton.resize(30, 30)
        self.mainwidgetbutton.move(10,0)
        self.mainwidgetbutton.setStyleSheet("background-color:#bbbbbb")
        self.mainwidgetbutton.clicked.connect(lambda:self.window.set_largeCentralPanel(self))
    def update_graph(self, new_x, new_y):
        self.xvals.append(new_x)
        self.yvals.append(new_y)
        last_time = self.xvals[-1]
        relative_xvals = [(x - last_time).total_seconds() for x in self.xvals]
        #Find what values, if any, are too old.
        too_old = [x < -self.x_timerange for x in relative_xvals]
        first_new_enough = too_old.index(False)
        self.xvals = self.xvals[first_new_enough:]
        self.yvals = self.yvals[first_new_enough:]
        self.plotline.setData(relative_xvals[first_new_enough:],self.yvals)
        
    def return_to_normal(self):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
    def enlarge(self,new_geometry):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, new_geometry[1], new_geometry[0], new_geometry[3], new_geometry[2])
