from PyQt5.QtWidgets import QPushButton
import pyqtgraph as pg
from skyfield.api import load, EarthSatellite, wgs84, utc

class gs_access():
    def __init__(self,window,initparams):
        #Iterate over everything in initparams.
        for key,value in initparams.items():
            #This does self.key = value, where key is a string.
            setattr(self, key, value)
        self.window = window
        self.box = pg.GraphicsLayoutWidget(window)
        self.window.grid.addWidget(self.box, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
        self.box.setStyleSheet("border:2px solid black; border-radius: 5px;")
        self.box.setBackground(self.color)

        self.access_plot = self.box.addPlot(axisItems = {'bottom': pg.DateAxisItem()})
        ts = load.timescale()
        
        #Load in all ground stations registered to the window
        gs_data = self.window.params['Groundstations']
        for gs in gs_data:
            #Filter for the one matching the name we're seeking
            if gs['Name'] == self.groundstation:
                gs_data = gs
                break
        groundstation = wgs84.latlon(gs_data['Lat'],gs_data['Lon'])
        for i, tle in enumerate(self.window.cross_module_vars['TLES'].values()):
            sat = EarthSatellite(*tle)
            startTime = ts.from_datetime(self.window.cross_module_vars['globaltime'].replace(tzinfo=utc))
            endTime = startTime + 1 #calculate one day
            t,events = sat.find_events(groundstation, startTime, endTime)
            # list of start and end times for each bar
            bar_pairs = []
            curr_barpair = []
            for time, event_type in zip(t,events):
                if event_type == 0:
                    curr_barpair = [float(time.utc_strftime("%s"))]
                if event_type == 2:
                    #handle the case where we are currently in a pass, and there was no start
                    if curr_barpair == []:
                        curr_barpair.append(float(startTime.utc_strftime("%s")))
                    curr_barpair.append(float(time.utc_strftime("%s")))
                    bar_pairs.append(curr_barpair)
            for bp in bar_pairs:
                bar = pg.BarGraphItem(x0=[bp[0]], x1 = [bp[1]], y = i+1, height=0.5,brush = 'r')
                self.access_plot.addItem(bar)
        ticks = [(i+1, str(tle)) for i, tle in enumerate(self.window.cross_module_vars['TLES'].keys())]
        self.access_plot.getAxis("left").setTicks((ticks,[]))


        
        #Expansion button to make the main widget thing
        self.mainwidgetbutton = QPushButton("⛶",self.box)
        self.mainwidgetbutton.resize(30, 30)
        self.mainwidgetbutton.move(10,0)
        self.mainwidgetbutton.setStyleSheet("background-color:#bbbbbb")
        self.mainwidgetbutton.clicked.connect(lambda:self.window.set_largeCentralPanel(self))
    #Go back to normal size and location when something else becomes the big widget
    def return_to_normal(self):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
    def enlarge(self,new_geometry):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, new_geometry[1], new_geometry[0], new_geometry[3], new_geometry[2])
