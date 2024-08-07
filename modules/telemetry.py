from PyQt5.QtWidgets import QPushButton
import pyqtgraph as pg
from lightstreamer.client import LightstreamerClient,Subscription
import time

class telemetry():
    def __init__(self,window,initparams):
        print("Initializing telemetry item")
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
        self.xvals = [0]
        self.yvals = [0]
        client = LightstreamerClient("https://push.lightstreamer.com","ISSLIVE")
        client.connectionOptions.setSlowingEnabled(False)
        
        sub = Subscription("MERGE",
            items = [self.telemetry_item],
            fields=["TimeStamp", "Value"])
        sub.addListener(self) #Add self as listener, onItemUpdate will be called whenever that happens
        client.subscribe(sub)
        client.connect()

        #Expansion button to make the main widget thing
        self.mainwidgetbutton = QPushButton("⛶",self.box)
        self.mainwidgetbutton.resize(30, 30)
        self.mainwidgetbutton.move(10,0)
        self.mainwidgetbutton.setStyleSheet("background-color:#bbbbbb")
        self.mainwidgetbutton.clicked.connect(lambda:self.window.set_largeCentralPanel(self))
    def update_graph(self):
        last_time = self.xvals[-1]
        relative_xvals = [x - last_time for x in self.xvals]
        #Find what values, if any, are too old.
        too_old = [x < -self.x_timerange for x in relative_xvals]
        first_new_enough = too_old.index(False)
        self.xvals = self.xvals[first_new_enough:]
        self.yvals = self.yvals[first_new_enough:]
        self.plotline.setData(relative_xvals[first_new_enough:],self.yvals)
        
    def onItemUpdate(self, update):
        try:
          with open("collected_data.txt","a") as f:
            self.xvals.append(float(update.getValue('TimeStamp'))*3600)
            self.yvals.append(float(update.getValue('Value')))
            f.write(f"{update.getItemName()}: {update.getValue('Value')} {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} {update.getValue('TimeStamp')}\n")
            self.update_graph()
        except Exception as e:
          print("Exception!")
          print(e)
    def return_to_normal(self):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
    def enlarge(self,new_geometry):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, new_geometry[1], new_geometry[0], new_geometry[3], new_geometry[2])

