from PyQt5 import QtCore
from PyQt5.QtWidgets import QPushButton, QGraphicsEllipseItem
import pyqtgraph as pg
import numpy as np
from skyfield.api import load, EarthSatellite, wgs84, utc

# Transform alt, az numbers to the xy native plot coordinates
def polar_plot_coords(alt, az):
    # center of plot is at 0, but alt-wise is 90.
    r_value = 90 - alt
    # standard coords puts 0 at east, counterclockwise.
    # azimuth puts 0 at north, clockwise.
    theta_value = 90 - az
    theta_value = theta_value * np.pi/180
    x = r_value * np.cos(theta_value)
    y = r_value * np.sin(theta_value)
    return x,y
# The reverse of the prior function, used for exporting
def xy_to_altaz(x, y):
    alt = 90 - np.sqrt(x**2 + y**2)
    az = (90 - np.arctan2(y,x) * 180/np.pi) % 360
    return alt, az
class plotted_satellite():
    def __init__(self,ID,color,plot_obj,window, skyfield_gs):
        self.ID = ID
        self.color = color
        self.plot_obj = plot_obj
        self.window = window
        self.gs = skyfield_gs
        # instantaneous location of sat
        self.dot = self.plot_obj.plot([],[],symbolBrush=color)
        # path of sat across sky
        self.arc = self.plot_obj.plot([],[],pen=pg.mkPen(color))

    def update(self):
        TLE = self.window.cross_module_vars['TLES'][self.ID]
        sat = EarthSatellite(*TLE)
        ts = load.timescale()
        time = ts.from_datetime(self.window.cross_module_vars['globaltime'].replace(tzinfo=utc))
        sight_diff = sat - self.gs
        sight_vector = sight_diff.at(time)
        alt,az,dist = sight_vector.altaz()
        if alt.degrees > 0:
            plotcoords = polar_plot_coords(alt.degrees,az.degrees)
            self.dot.setData([plotcoords[0]],[plotcoords[1]])
        else:
            self.dot.setData([],[])
        #draw the line starting 10 minutes before
        line_starttime = time.tt - 600/86400
        line_xy = []
        for i in range(0,1200,20):
            line_time = ts.tt_jd(line_starttime + i/86400)
            sight_vector = sight_diff.at(line_time)
            alt,az,dist = sight_vector.altaz()
            if alt.degrees > 0:
                line_xy.append(polar_plot_coords(alt.degrees,az.degrees))
        self.arc.setData(*zip(*line_xy))

class pass_polar():
    def __init__(self,window,initparams):
        #Iterate over everything in initparams.
        for key,value in initparams.items():
            #This does self.key = value, where key is a string.
            setattr(self, key, value)
        self.window = window
        self.box = pg.GraphicsLayoutWidget(window)
        self.window.grid.addWidget(self.box, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
        self.box.setStyleSheet("border:2px solid black; border-radius: 5px;")
        #Load in all ground stations registered to the window
        gs_data = self.window.params['Groundstations']
        for gs in gs_data:
            #Filter for the one matching the name we're seeking
            if gs['Name'] == self.groundstation:
                gs_data = gs
                break
        self.groundstation = wgs84.latlon(gs_data['Lat'],gs_data['Lon'])

        #pyqtgraph does not have a built in polar plot handler. Make our own.
        #https://stackoverflow.com/questions/57174173/polar-coordinate-system-in-pyqtgraph
        self.polar_plot = self.box.addPlot()
        self.polar_plot.hideAxis('bottom')
        self.polar_plot.hideAxis('left')
        self.polar_plot.setAspectLocked()
        self.polar_plot.setRange(xRange = [-90,90],yRange=[-90,90],padding=0)
        # draw axis rings
        for r in range(0, 90, 10):
            circle = QGraphicsEllipseItem(-r, -r, r*2, r*2)
            thick_lines = [30,60]
            circle.setPen(pg.mkPen(0.5 if r in thick_lines else 0.2))
            self.polar_plot.addItem(circle)
        # draw final thick one for horizon
        circle = QGraphicsEllipseItem(-90, -90, 180, 180)
        circle.setPen(pg.mkPen(1.0))
        self.polar_plot.addItem(circle)
        # draw crosshairs
        for theta in range(0, 360, 45):
            self.polar_plot.plot([0,90*np.sin(theta*np.pi/180)], [0,90*np.cos(theta*np.pi/180)], pen=pg.mkPen(0.2))
        
        self.satellites = []
        for sat in self.SATS:
            self.satellites.append(plotted_satellite(sat["ID"],sat["Color"],self.polar_plot,self.window, self.groundstation))

        #Set up QTimer, every time it runs its cycle (set by self_update_ms) it will run self.update, which updates map
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
    def export_data(self):
        data_out = {}
        data_out['satellites'] = []
        for sat in self.satellites:
            sat_data = {}
            sat_data['ID'] = sat.ID
            altaz = [xy_to_altaz(x,y) for x,y in zip(*sat.arc.getData())]
            sat_data["ALT/AZ"] = altaz
            data_out['satellites'].append(sat_data)
        return data_out
    #Go back to normal size and location when something else becomes the big widget
    def return_to_normal(self):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
    def enlarge(self,new_geometry):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, new_geometry[1], new_geometry[0], new_geometry[3], new_geometry[2])
    def update(self):
        for sat in self.satellites:
            sat.update()