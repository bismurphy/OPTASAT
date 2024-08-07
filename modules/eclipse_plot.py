from PyQt5.QtWidgets import QPushButton
from PyQt5 import QtCore

import pyqtgraph as pg
from skyfield.api import load, EarthSatellite, wgs84, utc
import numpy as np

class eclipse_plot():
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

        self.sunlight_plot = self.box.addPlot(axisItems = {'bottom': pg.DateAxisItem()})
        
        self.updater = QtCore.QTimer()
        self.updater.timeout.connect(self.update)
        self.updater.start(self.self_update_ms)
        self.update()

        
        #Expansion button to make the main widget thing
        self.mainwidgetbutton = QPushButton("⛶",self.box)
        self.mainwidgetbutton.resize(30, 30)
        self.mainwidgetbutton.move(10,0)
        self.mainwidgetbutton.setStyleSheet("background-color:#bbbbbb")
        self.mainwidgetbutton.clicked.connect(lambda:self.window.set_largeCentralPanel(self))
    def update(self):
        self.sunlight_plot.clear()
        ts = load.timescale()
        
        TLE = self.window.cross_module_vars['TLES'][self.sat_id]
        sat = EarthSatellite(*TLE)
        startTime = ts.from_datetime(self.window.cross_module_vars['globaltime'].replace(tzinfo=utc))
        endTime = startTime + 1 #calculate one day
        timespan = ts.tt_jd(np.linspace(startTime.tt,endTime.tt,86400))
        
        eph = load('de421.bsp')
        lit_state = sat.at(timespan).is_sunlit(eph)
        
        
        # list of start and end times for each bar
        bar_pairs = []
        was_lit = lit_state[0]
        if was_lit: #if we start lit, start the first bar right away
            current_barpair = [float(timespan[0].utc_strftime("%s"))]
        else:
            current_barpair = []
        for time, islit in zip(timespan,lit_state):
            if islit and not was_lit:
                current_barpair = [float(time.utc_strftime("%s"))]
                was_lit = True
            elif not islit and was_lit:
                current_barpair.append(float(time.utc_strftime("%s")))
                bar_pairs.append(current_barpair)
                current_barpair = []
                was_lit = False
        for bp in bar_pairs:
            bar = pg.BarGraphItem(x0=[bp[0]], x1 = [bp[1]], y = 1, height=0.5,brush = 'orange')
            self.sunlight_plot.addItem(bar)
        ticks = [(1, f"Sunlight times for {self.sat_id}")]
        self.sunlight_plot.getAxis("left").setTicks((ticks,[]))
    #Go back to normal size and location when something else becomes the big widget
    def return_to_normal(self):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
    def enlarge(self,new_geometry):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, new_geometry[1], new_geometry[0], new_geometry[3], new_geometry[2])
