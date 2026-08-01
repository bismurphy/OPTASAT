from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QLineEdit
from PyQt5.QtGui import QFont
from PyQt5 import QtCore
import pyqtgraph as pg
import numpy as np
import os

#matplotlib configuration
import matplotlib
matplotlib.use('QT5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.patches import Polygon
from matplotlib.widgets import TextBox

#skyfield space dynamics
from skyfield.api import Star, load, wgs84, EarthSatellite, utc
from skyfield.data import hipparcos
from skyfield import named_stars
from skyfield.units import Angle
from skyfield.framelib import ecliptic_frame

#constants
from skyfield.constants import ERAD, RAD2DEG
TWOPI = 2 * np.pi
HALFPI = np.pi / 2
SUN_IMAGE =  plt.imread(os.path.dirname(os.path.realpath(__file__))  +'/sun.png')
MOON_IMAGE = plt.imread(os.path.dirname(os.path.realpath(__file__))  +'/moon.png')

#how many points to use when drawing the earth occlusion shape
CIRCLE_RESOLUTION = 1000
#How large to draw the images of the sun and moon. Note this is much larger than real-life.
SUN_SIZE = 0.15
MOON_SIZE = 0.15

#The haversine function
def hav(value):
    return (1 - np.cos(value)) / 2
    
#The archaversine function
def archav(value):
    if 0 < value < 1:
        return np.arccos(1 - 2 * value)
    return None

#Get a set of stars, and a parallel list of their normal-English names. Optional mag_limit
#will result in only returning stars with magnitudes that are below that limit.
def get_stars_with_names(mag_limit=100):
    with load.open(hipparcos.URL) as f:
        df = hipparcos.load_dataframe(f)
        df_filtered = df[df['magnitude'] <= mag_limit]
        hip_numbers = df_filtered.index.values.tolist()
        #Produce a dictionary that takes HIP numbers as keys and returns names
        name_dict = {v: k for k, v in named_stars.named_star_dict.items()}
        star_names = []
        for star in hip_numbers:
            if star in name_dict:
                star_names.append(name_dict[star])
            else:
                star_names.append("HIP " + str(star))
        stars = df_filtered.values.tolist()
        stars_to_return = []
        for s in stars:
            mag,ra_deg,dec_deg = s[:3]
            ra_angle = Angle(degrees = ra_deg)
            dec_angle = Angle(degrees = dec_deg)
            newstar = Star(ra = ra_angle, dec = dec_angle)
            stars_to_return.append(newstar)
    return stars_to_return, star_names, df_filtered['magnitude']

#Gets the phase of the moon, as seen by an observer
def get_moon_phase(observer,moon,sun,time):
    sun_longitude = (sun - observer).at(time).frame_latlon(ecliptic_frame)[1]
    moon_longitude = (moon - observer).at(time).frame_latlon(ecliptic_frame)[1]
    return (moon_longitude.degrees - sun_longitude.degrees) % 360

class starmap():
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

        #Load solar system bodies
        planets = load('de421.bsp')
        self.earth = planets['earth']
        self.moon = planets['moon']
        self.sun = planets['sun']

        #Create the matplotlib graph
        self.fig, self.ax = plt.subplots()
        self.populate_graph()
        self.plotWidget = FigureCanvas(self.fig)
        self.update_plot()

        #Add star annotations to matplotlib graph
        self.annot = self.ax.annotate("", xy=(0,0), xytext=(20,20),textcoords="offset points",
                    bbox=dict(boxstyle="round", fc="w"),
                    arrowprops=dict(arrowstyle="->",color='w'))
        self.annot.set_visible(False)
        self.fig.canvas.mpl_connect("motion_notify_event", self.hover)

        #Create a plot holder and place the plot inside of it
        self.plotHolder = QVBoxLayout(self.box)
        self.plotHolder.setContentsMargins(10, 10, 10, 10)      
        self.plotHolder.addWidget(self.plotWidget)
        #Add star search box (matplotlib has a TextBox widget that doesn't seem to work here)
        # leave  a margin to fit the search box underneath
        self.searchbox = QLineEdit(self.box)
        self.searchbox.setFont(QFont("Helvetica",16))
        self.searchbox.setPlaceholderText("Enter a star name to search for...")
        self.searchbox.returnPressed.connect(self.run_starsearch)
        self.plotHolder.addWidget(self.searchbox)

        #Expansion button to make the main widget thing
        self.mainwidgetbutton = QPushButton("⛶",self.box)
        self.mainwidgetbutton.resize(30, 30)
        self.mainwidgetbutton.move(10,0)
        self.mainwidgetbutton.setStyleSheet("background-color:#bbbbbb")
        self.mainwidgetbutton.clicked.connect(lambda:self.window.set_largeCentralPanel(self))

        #Set up QTimer, every time it runs its cycle (set by self_update_ms) it will run self.update, which updates map
        self.updater = QtCore.QTimer()
        self.updater.timeout.connect(self.update_plot)
        self.updater.start(self.self_update_ms)
        

    def update_plot(self):
        plot_time = self.ts.from_datetime(self.window.cross_module_vars['globaltime'].replace(tzinfo=utc))
        for i in self.plotted_objects:
            i.remove()
        
        sun_ra,sun_dec,_ = (self.sun-self.earth-self.sat_obj).at(plot_time).radec()
        moon_ra,moon_dec,_ = (self.moon-self.earth-self.sat_obj).at(plot_time).radec()
        # first plot keepout zones, so they end up in the background
        plotted_keepouts = []
        if hasattr(self,'keepouts'):
            for keepout_def in self.keepouts:
                center = keepout_def['center']
                if type(center) == str:
                    if center == "moon":
                        center = [moon_ra._degrees, moon_dec.degrees]
                    if center == "sun":
                        center = [sun_ra._degrees, sun_dec.degrees]
                    if center == "earth":
                        sat_ra,sat_dec,_ = self.sat_obj.at(plot_time).radec()
                        earth_ra = (sat_ra.degrees + np.pi) % TWOPI
                        earth_dec = -sat_dec.degrees
                        center = [earth_ra._degrees, earth_dec.degrees]
                if type(center) == list:
                    # convert center degrees to radians
                    center = [x / RAD2DEG for x in center]
                radius_degrees = keepout_def['radius'] / RAD2DEG
                plotted_keepouts.extend(self.plot_circle(center[1], center[0], radius_degrees, keepout_def['color']))
        #These functions are all time-dependent and draw everything on the background of stars.
        satellite_mark = self.mark_satellite(self.sat_obj,plot_time)
        earth_polygons = self.draw_earth(self.sat_obj,plot_time)
        sunstamp = self.plot_stamp(sun_ra,sun_dec,SUN_IMAGE,SUN_SIZE)
        moonstamp = self.plot_stamp(moon_ra,moon_dec,MOON_IMAGE,MOON_SIZE)
        moon_phase = get_moon_phase(self.earth+self.sat_obj, self.moon, self.sun,plot_time)
        moonmask = self.draw_moonmask(moon_phase,MOON_SIZE,moon_ra.radians,moon_dec.radians)
        plotted_othersats = self.draw_othersats(self.sat_obj, self.otherSatIDs, plot_time)
        #Refresh the plot based on the new objects we made
        self.plotWidget.draw()
        self.plotted_objects = [*plotted_keepouts, satellite_mark,*earth_polygons,sunstamp,moonstamp,moonmask, *plotted_othersats]
        
    def populate_graph(self):
        self.ax.set_facecolor("black")
        self.ax.set_xlim(0,TWOPI)
        self.ax.set_ylim(-HALFPI,HALFPI)
        self.ax.set_aspect("equal")
        #Change the axis labels to be standard units - Hours for RA, Degrees for DEC
        plt.xlabel("Right ascension (HOURS)")
        xtick_locations = np.linspace(0,TWOPI,13)
        self.ax.set_xticks(xtick_locations)
        self.ax.set_xticklabels([round(x * 24 / TWOPI) for x in xtick_locations])
        plt.ylabel("Declination (DEGREES)")
        ytick_locations = np.linspace(-HALFPI,HALFPI,13)
        self.ax.set_yticks(ytick_locations)
        self.ax.set_yticklabels([round(y * RAD2DEG) for y in ytick_locations])
        self.ax.grid(which='major',axis='both', color='lightgrey', linestyle=':', linewidth=0.5,zorder=0)
        self.ax.set_axisbelow(True)
        self.ax.invert_xaxis()

        self.ts = load.timescale()
        time = self.ts.from_datetime(self.window.cross_module_vars['globaltime'].replace(tzinfo=utc))
        self.star_field, self.star_names = self.draw_starmap(self.star_mag_limit,time)
        sat_dict = self.window.cross_module_vars['sat_dicts'][self.sat_id]
        self.sat_obj = EarthSatellite.from_omm(self.ts, sat_dict)

        self.plotted_objects = []

    def draw_starmap(self,magnitude_limit,plot_time):
        global bright_stars
        bright_stars, star_names, mags = get_stars_with_names(magnitude_limit)
        ras = []
        decs = []
        for star in bright_stars:
            astrometric = self.earth.at(plot_time).observe(star)
            ra, dec, distance = astrometric.radec()
            ras.append(ra.radians)
            decs.append(dec.radians)
        #Scale magnitudes so they fit the size better.
        #First invert so higher = brighter
        dimmest = max(mags)
        mags = dimmest - mags
        #Mags are logarithmic. Undo the logarithm.
        mags = 2.512 ** mags
        #Now we have a linear scale. Now normalize it from 0 to 1.
        smallest = min(mags) - 1
        largest = max(mags)
        mags = 100*(mags - smallest) / (largest - smallest)
        return self.ax.scatter(ras,decs, s=mags,color='w',marker="*"),star_names

    #These functions enable mouseover on star names
    def update_annot(self,ind):
        pos = self.star_field.get_offsets()[ind["ind"][0]]
        self.annot.xy = pos
        text = " ".join([self.star_names[n] for n in ind["ind"]])
        self.annot.set_text(text)
        global bright_stars
        star_index = ind["ind"][0] 
        ra = str(round(bright_stars[star_index].ra.radians,3))
        dec = str(round(bright_stars[star_index].dec.radians,3))

        #self.ax.set_title(text + ":" + "RA=" + ra + "DEC=" + dec)
    def hover(self,event):
        vis = self.annot.get_visible()
        if event.inaxes == self.ax:
            cont, ind = self.star_field.contains(event)
            if cont:
                self.update_annot(ind)
                self.annot.set_visible(True)
                self.fig.canvas.draw_idle()
            else:
                if vis:
                    self.annot.set_visible(False)
    def run_starsearch(self):
        starname = self.searchbox.text()
        self.searchbox.setText("")
        upper_names = [s.upper() for s in self.star_names]
        if starname.upper() not in upper_names:
            self.searchbox.setPlaceholderText(f"The star {starname} was not found.")
            return
        self.searchbox.setPlaceholderText("Enter a star name to search for...")
        star_index = upper_names.index(starname.upper())
        ind = {"ind":np.array([star_index])}
        self.update_annot(ind)
        self.annot.set_visible(True)
        self.fig.canvas.draw_idle()
        
    def mark_satellite(self,sat,plot_time):
        sat_ra,sat_dec,_ = sat.at(plot_time).radec()
        sat_ra = sat_ra.radians
        sat_dec = sat_dec.radians
        return self.ax.scatter(sat_ra,sat_dec,s=200,color='r',marker='+')
    
    def draw_earth(self,sat,plot_time):
        sat_ra,sat_dec,sat_dist = sat.at(plot_time).radec()
        #Draw in the earth
        #earth is the opposite direction of sat
        earth_ra = (sat_ra.radians + np.pi) % TWOPI
        earth_dec = -sat_dec.radians
        #Draws the earth on the map, which may or may not be a ring depending on alignments of objects
        distance_to_sat = sat.at(plot_time).distance().m
        earth_angular_radius = np.arcsin(ERAD/distance_to_sat)
        return self.plot_circle(earth_dec, earth_ra, earth_angular_radius, "blue")
    
    #Given a center lat/long and angular radius, returns a set of longs/lats to represent that circle.
    def plot_circle(self, center_lat, center_lon, radius, color):
        plotted_polygons = [] #Keep track of what we end up plotting so we can return them
        # Start by getting the set of points we need to plot.
        # https://www.movable-type.co.uk/scripts/latlong.html has "Destination point given distance and bearing from start point"
        # So generate bearings from 0 to 2pi, and travel the required radius.
        points_to_plot = []
        bearings = np.linspace(0, TWOPI, CIRCLE_RESOLUTION)
        lats = np.arcsin(np.sin(center_lat) * np.cos(radius) +
                        np.cos(center_lat) * np.sin(radius) * np.cos(bearings))
        lons = center_lon + np.arctan2(np.sin(bearings) * np.sin(radius) * np.cos(center_lat),
                                        np.cos(radius) - np.sin(center_lat) * np.sin(lats))
        points_to_plot = np.column_stack([lons, lats])

        # If we pass over either of the poles, extend the polygon points to cover the pole. Do this by first detecting the pole:
        if(abs(center_lat) + radius > HALFPI):
            # Correct any reaching beyond standard range of 0 to 2pi
            points_to_plot[:, 0] %= TWOPI
            # Sorts by x coordinate to eliminate the necessary hop over antimeridian
            points_to_plot = points_to_plot[points_to_plot[:, 0].argsort()]
            # add points at corners to make polygon fill whole area above the line
            pole_lon = np.sign(center_lat) * HALFPI
            points_to_plot = np.vstack([[0,pole_lon], points_to_plot, [TWOPI,pole_lon]])
            plotted_polygons.append(self.ax.add_patch(Polygon(points_to_plot,color=color,alpha=0.5,linewidth=2)))
        # If we didn't pass over a pole, check if we went outside standard coordinates.
        elif np.any((lons < 0) | (lons > TWOPI)):
            # Create a second copy polygon, shifted by 2pi to cover the other axis. Therefore we will actually have two
            # polygons, but each cuts off at 0 or 2pi.
            second_polygon = points_to_plot.copy()
            # determine the direction to shift the second one based on the center longitude.
            # If greater than pi, shift down.
            second_polygon -= [TWOPI * np.sign(center_lon - np.pi), 0]
            plotted_polygons.append(self.ax.add_patch(Polygon(points_to_plot,color=color,alpha=0.5,linewidth=2)))
            plotted_polygons.append(self.ax.add_patch(Polygon(second_polygon,color=color,alpha=0.5,linewidth=2)))
        # Not far enough toward any axis to cross over it, just plot the polygon as a single simple blob
        else:
            plotted_polygons.append(self.ax.add_patch(Polygon(points_to_plot,color=color,alpha=0.5,linewidth=2)))
        return plotted_polygons
    
    #Used for placing sun and moon images.
    def plot_stamp(self,target_ra, target_dec, target_image, size):
        #Gets vector from sat to sun and converts to radec
        target_ra = target_ra.radians
        target_dec = target_dec.radians
        image_extent = [target_ra - size, target_ra + size,target_dec - size, target_dec + size]
        return self.ax.imshow(target_image,extent=image_extent,zorder=0.5)
    #Make a shadow over the proper part of the moon to show its phase
    def draw_moonmask(self, phase,moon_size,center_x,center_y):
        #Start from the top and draw a circle going down
        y_vals_1 = np.linspace(1,-1,1000)
        x_vals_1 = center_x + (moon_size if phase < 180 else -moon_size) * np.sqrt(1-y_vals_1**2)
        y_vals_1 *= moon_size
        y_vals_1 += center_y
        #Now from bottom up, draw the curve.
        y_vals_2 = np.linspace(-1,1,1000)
        #How far displaced is the non-circular portion from center
        x_displacement = (phase % 180 / 90) - 1
        x_displacement *= moon_size
        x_vals_2 = center_x + x_displacement*np.sqrt(1-y_vals_2**2)
        y_vals_2 *= moon_size
        y_vals_2 += center_y
        points = list(zip(x_vals_1,y_vals_1)) + list(zip(x_vals_2,y_vals_2))
        return self.ax.add_patch(Polygon(points,color='k',alpha=0.7,linewidth=0))
    # Draw the location in the sky of any other satellite, from the perspective of our base satellite
    def draw_othersats(self, self_sat, othersats, plot_time):
        plotted_sats = []
        for ID in othersats:
            other_sat_dict = self.window.cross_module_vars['sat_dicts'][ID]
            other_sat = EarthSatellite.from_omm(self.ts, other_sat_dict)
            sat_ra,sat_dec,_ = (other_sat - self_sat).at(plot_time).radec()
            sat_ra = sat_ra.radians
            sat_dec = sat_dec.radians
            plotted_sats.append(self.ax.scatter(sat_ra,sat_dec,s=200,color='orange',marker='2'))
        return plotted_sats


    #Go back to normal size and location when something else becomes the big widget
    def return_to_normal(self):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
    def enlarge(self,new_geometry):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, new_geometry[1], new_geometry[0], new_geometry[3], new_geometry[2])

