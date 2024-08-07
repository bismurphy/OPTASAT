from PyQt5 import QtCore
from PyQt5.QtWidgets import QPushButton, QVBoxLayout
import pyqtgraph as pg
import shapefile
import os
from skyfield.api import load, EarthSatellite, wgs84, utc
from skyfield.constants import ERAD #earth radius

import matplotlib
matplotlib.use('QT5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvas
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection

import numpy as np

#The haversine function
def hav(value):
    return (1 - np.cos(value)) / 2

#The archaversine function
def archav(value):
    if 0 < value < 1:
        return np.arccos(1 - 2 * value)
    return None

def angular_SSP_distance(SSP, ground_point):
    #This uses the Haversine Formula.
    lat1,lon1 = SSP
    lon2,lat2 = ground_point #shapefile specifies lon first!
    lat1,lon1,lon2,lat2 = [x * np.pi/180 for x in [lat1,lon1,lon2,lat2]] #All to radians 
    hav_theta = hav(lat2-lat1) + np.cos(lat1) * np.cos(lat2) * hav(lon2-lon1)
    theta = archav(hav_theta)
    return theta

class ground_view():
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

        #load relative file path from this script
        self.shape_file = shapefile.Reader(os.path.dirname(os.path.realpath(__file__))  + "/" + 
                                           "shapefile/ne_50m_admin_0_countries.cpg")
        self.TLE = self.window.cross_module_vars['TLES'][self.sat_id]

        self.fig, self.ax = plt.subplots()
        self.ax.set_facecolor("lightblue")
        self.plotWidget = FigureCanvas(self.fig)

        #Create a plot holder and place the plot inside of it
        self.plotHolder = QVBoxLayout(self.box)
        self.plotHolder.setContentsMargins(10, 10, 10, 10)      
        self.plotHolder.addWidget(self.plotWidget)

        
        #Expansion button to make the main widget thing
        self.mainwidgetbutton = QPushButton("⛶",self.box)
        self.mainwidgetbutton.resize(30, 30)
        self.mainwidgetbutton.move(10,0)
        self.mainwidgetbutton.setStyleSheet("background-color:#bbbbbb")
        self.mainwidgetbutton.clicked.connect(lambda:self.window.set_largeCentralPanel(self))

        #Set up QTimer, every time it runs its cycle (set by self_update_ms) it will run self.update, which updates map
        self.updater = QtCore.QTimer()
        self.updater.timeout.connect(self.update)
        self.updater.start(self.self_update_ms)
        self.update()
    def update(self):
        # remove all patches, to generate new ones
        self.ax.patches.clear()
        sat = EarthSatellite(*self.TLE)
        ts = load.timescale()
        time = ts.from_datetime(self.window.cross_module_vars['globaltime'].replace(tzinfo=utc))
        
        satpos = sat.at(time)
        now_lat,now_lon = wgs84.latlon_of(satpos)
        SSP = [now_lat.degrees, now_lon.degrees]
        # Calculate angular radius of the footprint of the sensor view. This is angle from SSP, to center of
        # earth, to the edge of the FOV
        # How: Draw a triangle with points at center of earth, at satellite, and at edge of FOV.
        # Label angles: Angle A at satellite, B at center of earth, C at edge of FOV.
        # Then sides are across from angles. Side a is center of earth to edge of FOV, so length is earth radius.
        # Side b is the "view-line" of the satellite. Side c is the known orbital altitude.
        # We have known A and a, so apply law of sines to get angle C from side c. Then with two angles,
        # get the third by summing to 180. This gives earth central angle.
        angle_A = self.halfangle_fov_deg * np.pi/180
        side_a = ERAD / 1000 #earth radius in meters, convert to km
        sinelaw_ratio = np.sin(angle_A) / side_a
        side_c = np.linalg.norm(satpos.position.km)
        # Need to subtract from pi to get the solution where C > pi/2 (arcsine ambiguity)
        angle_C = np.pi - np.arcsin(sinelaw_ratio*side_c)
        angle_B = np.pi - angle_C - angle_A
        # don't actually need this but we'll calculate it for completeness. It's the slant range to the edge of FOV
        side_b = np.sin(angle_B)/sinelaw_ratio
        

        recs = self.shape_file.records()
        shapes = self.shape_file.shapes()
        for shape in shapes:
            ptchs = []
            pts = np.array(shape.points)
            points_in = []
            for point in pts:
                dist = angular_SSP_distance(SSP,point)
                if dist < angle_B:
                    points_in.append(point)
                # if it's on the "back" side of earth, just abandon the whole shape
                elif dist > np.pi/2:
                    continue
            prt = shape.parts
            par = list(prt) + [pts.shape[0]]
            for pij in range(len(prt)):
                 ptchs.append(Polygon(pts[par[pij]:par[pij+1]]))
            if len(points_in) > 0:
                self.ax.add_collection(PatchCollection(ptchs,facecolor="lightgreen",edgecolor='k', linewidths=1))
        footprint_radius_deg = angle_B * 180/np.pi
        self.ax.set_xlim(SSP[1] - footprint_radius_deg,SSP[1] + footprint_radius_deg)
        self.ax.set_ylim(SSP[0] - footprint_radius_deg,SSP[0] + footprint_radius_deg)
        self.plotWidget.draw()
    #Go back to normal size and location when something else becomes the big widget
    def return_to_normal(self):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
    def enlarge(self,new_geometry):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, new_geometry[1], new_geometry[0], new_geometry[3], new_geometry[2])
