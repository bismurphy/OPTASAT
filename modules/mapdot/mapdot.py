from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QPushButton,QWidget,QAction, QDialog, QGridLayout, QLabel, QInputDialog, QSpinBox
import pyqtgraph as pg
import numpy as np
#For loading image file
import os
from skyfield.api import load, EarthSatellite, wgs84, utc
from skyfield.elementslib import osculating_elements_of
from skyfield.framelib import itrs
import datetime

EARTH_RADIUS = 6371
HALFPI = np.pi/2
TWOPI = np.pi*2

#The haversine function
def hav(value):
    return (1 - np.cos(value)) / 2
    
#The archaversine function
def archav(value):
    if 0 < value < 1:
        return np.arccos(1 - 2 * value)
    
class plotted_satellite():
    def __init__(self,name,ID,color,fov,plot_obj,window):
        self.name = name
        self.ID = ID
        self.color = color
        self.fov = fov
        self.plot_obj = plot_obj
        self.window = window
        self.dot = self.plot_obj.plot([0],[0],symbolBrush=color)

        # 2 for each to account for wraparound at +/- 180
        self.forwardline1 = self.plot_obj.plot(pen=pg.mkPen(color=color,width=2))
        self.forwardline2 = self.plot_obj.plot(pen=pg.mkPen(color=color,width=2))
        self.backwardline1 = self.plot_obj.plot(pen=pg.mkPen(color=color, style=QtCore.Qt.DashLine,width=2))
        self.backwardline2 = self.plot_obj.plot(pen=pg.mkPen(color=color, style=QtCore.Qt.DashLine,width=2))

        # Also 2 in case we need them for east/west
        self.footprint_plot1 = self.plot_obj.plot(pen=pg.mkPen(color=color))
        self.footprint_plot2 = self.plot_obj.plot(pen=pg.mkPen(color=color))
        
        #Make a plot object for the sensor view patch
        self.sensor_plot = pg.ScatterPlotItem(size=4,pen=pg.mkPen(None),brush=pg.mkBrush(color=color))
        self.plot_obj.addItem(self.sensor_plot)

        self.plotted_name = pg.TextItem(self.name,anchor=(0.5,0.1),color=color) #anchor sets position of text wrt x,y location
        self.plot_obj.addItem(self.plotted_name)
        
        self.offaxis_mag = 0 #angle between boresight and nadir
        self.offaxis_dir = 0 #direction in which the boresight angle is away from nadir
        
    def update(self):
        TLE = self.window.cross_module_vars['TLES'][self.ID]
        sat = EarthSatellite(*TLE)
        ts = load.timescale()
        time = ts.from_datetime(self.window.cross_module_vars['globaltime'].replace(tzinfo=utc))
        satpos = sat.at(time)
        self.now_lat,self.now_lon = wgs84.latlon_of(satpos)
        self.dot.setData([self.now_lon.degrees],[self.now_lat.degrees])
        self.plotted_name.setPos(self.now_lon.degrees, self.now_lat.degrees)
        sat_period_minutes = osculating_elements_of(satpos).period_in_days*1440
        
        # Plotting the ground track for the next orbit
        next_period = time + datetime.timedelta(minutes=sat_period_minutes)
        timerange = ts.tt_jd(np.linspace(time.tt,next_period.tt,100))
        geocentric = sat.at(timerange)
        lat, lon = wgs84.latlon_of(geocentric)
        points = list(zip(lon.degrees,lat.degrees))
        #detect, for each point, whether it's a jump (wrap at 180) from the previous point
        has_jump = [abs(points[i][0] - points[i-1][0]) > 20 for i in range(1,len(points))]
        if any(has_jump):
            jump_index = has_jump.index(True)+1
            self.forwardline1.setData(*list(zip(*points[:jump_index])))
            self.forwardline2.setData(*list(zip(*points[jump_index:])))
        else:
            self.forwardline1.setData(*list(zip(*points)))
            self.forwardline2.setData([],[])

        last_period = time - datetime.timedelta(minutes=sat_period_minutes)
        timerange = ts.tt_jd(np.linspace(time.tt,last_period.tt,100))
        geocentric = sat.at(timerange)
        lat, lon = wgs84.latlon_of(geocentric)
        points = list(zip(lon.degrees,lat.degrees))
        #detect, for each point, whether it's a jump (wrap at 180) from the previous point
        has_jump = [abs(points[i][0] - points[i-1][0]) > 20 for i in range(1,len(points))]
        if any(has_jump):
            jump_index = has_jump.index(True)+1
            self.backwardline1.setData(*list(zip(*points[:jump_index])))
            self.backwardline2.setData(*list(zip(*points[jump_index:])))
        else:
            self.backwardline1.setData(*list(zip(*points)))
            self.backwardline2.setData([],[])
        #Now draw the (potentially displaced) sensor footprint
        #Note: Using -1 * position to get a nadir pointing vector
        if self.fov != 0:
            satpos_ECEF = satpos.frame_xyz(itrs).km
            nadir = -1 * satpos_ECEF
            boresight = angle_offset_vector(nadir, self.offaxis_mag, self.offaxis_dir)
            footprint = get_footprint_points(satpos_ECEF,self.fov, boresight)
            self.sensor_plot.setData(*list(zip(*footprint)))

        #orbital distance from center of earth
        altitude = wgs84.height_of(geocentric[0]).km + EARTH_RADIUS
        # size in lat/long degrees of the footprint
        # this is the angle, at center of earth, between the sat and horizon
        footprint_size = np.arccos(EARTH_RADIUS/altitude) #comes from trig
        #List of polygons that need to be drawn
        footprint = get_footprint_polygons(self.now_lat.radians,self.now_lon.radians,footprint_size) #0.1 radians
        first_footprint = np.array(footprint[0])*180/np.pi
        self.footprint_plot1.setData(*list(zip(*first_footprint)))
        second_footprint = np.array(footprint[1])*180/np.pi
        self.footprint_plot2.setData(*list(zip(*second_footprint)))
        
    def show_controls(self):
        class BoresightControlDialog(QDialog):
            def __init__(self, sat_to_control):
                super().__init__()
                self.sat = sat_to_control
                self.setWindowTitle(sat_to_control.name + " Boresight control")
                self.setWindowModality(False) #enables interacting with main window even while dialog is up
                #populate UI elements
                self.grid = QGridLayout()
                self.magLabel = QLabel("Amount of boresight tilt from nadir")
                self.grid.addWidget(self.magLabel,0,0)
                self.magInput = QSpinBox()
                self.magInput.setValue(self.sat.offaxis_mag)
                self.magInput.setMaximum(90)
                self.grid.addWidget(self.magInput,0,1)

                self.dirLabel = QLabel("Compass direction of boresight tilt")
                self.grid.addWidget(self.dirLabel,1,0)
                self.dirInput = QSpinBox()
                self.dirInput.setValue(self.sat.offaxis_dir)
                self.dirInput.setMaximum(360)
                self.grid.addWidget(self.dirInput,1,1)

                self.fovLabel = QLabel("Sensor field of view (deg)")
                self.grid.addWidget(self.fovLabel,2,0)
                self.fovInput = QSpinBox()
                self.fovInput.setValue(self.sat.fov)
                self.fovInput.setMaximum(180)
                self.grid.addWidget(self.fovInput,2,1)

                self.magInput.valueChanged.connect(self.update_vals)
                self.dirInput.valueChanged.connect(self.update_vals)
                self.fovInput.valueChanged.connect(self.update_vals)
                self.setLayout(self.grid)
            def update_vals(self):
                new_mag = int(self.magInput.value())
                new_dir = int(self.dirInput.value())
                new_fov = int(self.fovInput.value())
                self.sat.offaxis_mag = new_mag
                self.sat.offaxis_dir = new_dir
                self.sat.fov = new_fov
        settingsWindow = BoresightControlDialog(self)
        settingsWindow.exec()
        
        
class mapdot():
    def __init__(self,window,initparams):
        #Iterate over everything in initparams.
        for key,value in initparams.items():
            #This does self.key = value, where key is a string.
            setattr(self, key, value)
        self.window = window
        self.box = pg.GraphicsLayoutWidget(window)
        self.window.grid.addWidget(self.box, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
        self.box.setStyleSheet("border:2px solid black; border-radius: 5px;")

        self.loaded_image = QtGui.QImage(os.path.dirname(os.path.realpath(__file__))  + '/background_map.png')
        self.image_array = pg.imageToArray(self.loaded_image)
        self.image_array[..., :3] = self.image_array[..., 2::-1] #Convert BGRA to RGBA
        self.image_array = np.flip(self.image_array,1) #Flip Y axis to increase upward.
        self.imageitem = pg.ImageItem(self.image_array)
        
        self.imageitem.setRect(-180,-90,360,180)

        self.map_plot = self.box.addPlot()
        self.map_plot.addItem(self.imageitem)
        self.map_plot.setRange(xRange = [-180,180],yRange=[-90,90],padding=0)
        self.satellites = []
        for sat in self.SATS:
            if "FOV" not in sat: #if no sensor is specified, make it zero
                sat["FOV"] = 0
            self.satellites.append(plotted_satellite(sat["Name"],sat["ID"],sat["Color"], sat["FOV"],self.map_plot,self.window))

        # Plot ground stations
        if 'Groundstations' in self.window.params:
            for gs in self.window.params['Groundstations']:
                gs_name = pg.TextItem(gs['Name'],anchor=(0.5,0.1)) #anchor sets position of text wrt x,y location
                self.map_plot.addItem(gs_name)
                gs_name.setPos(gs['Lon'],gs['Lat'])
                self.map_plot.plot([gs['Lon']],[gs['Lat']],symbolBrush="#FF8000")
        
        #This pair of lines prevents user from zooming out beyond the initial full-earth view. Keeps the map view full.
        range_ = self.map_plot.getViewBox().viewRange() 
        self.map_plot.getViewBox().setLimits(xMin=range_[0][0], xMax=range_[0][1],   
                             yMin=range_[1][0], yMax=range_[1][1])
        
        #Expansion button to make the main widget thing
        self.mainwidgetbutton = QPushButton("⛶",self.box)
        self.mainwidgetbutton.resize(30, 30)
        self.mainwidgetbutton.move(10,0)
        self.mainwidgetbutton.setStyleSheet("background-color:#bbbbbb")
        self.mainwidgetbutton.clicked.connect(lambda:self.window.set_largeCentralPanel(self))

        #Example of including things in the menu bar
        mapzoomreset = QAction(self.name + ": Reset map zoom",self.window)
        self.window.modulesMenu.addAction(mapzoomreset)
        mapzoomreset.triggered.connect(lambda: self.map_plot.enableAutoRange())
        #make panel for controlling the offset views
        offset_submenu = self.window.modulesMenu.addMenu("Show offset control panel")
        for sat in self.satellites:
            sat_control_button = QAction(sat.name, self.window)
            offset_submenu.addAction(sat_control_button)
            sat_control_button.triggered.connect(sat.show_controls)


        #Set up QTimer, every time it runs its cycle (set by self_update_ms) it will run self.update, which updates map
        self.updater = QtCore.QTimer()
        self.updater.timeout.connect(self.update)
        self.updater.start(self.self_update_ms)
        self.update()

    def update(self):
        for sat in self.satellites:
            sat.update()
    def export_data(self):
        sats_data = []
        for sat in self.satellites:
            sat_data = {"Name":sat.name,
                        "Lat": sat.now_lat.degrees,
                        "Lon": sat.now_lon.degrees,
                        "Off-nadir mag":sat.offaxis_mag,
                        "Off-nadir dir":sat.offaxis_dir}
            sats_data.append(sat_data)
        return {"sats":sats_data}
    #Go back to normal size and location when something else becomes the big widget
    def return_to_normal(self):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
    def enlarge(self,new_geometry):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, new_geometry[1], new_geometry[0], new_geometry[3], new_geometry[2])
def get_footprint_points(sat_pos, fov_deg, boresight_vec):
    cone_vectors = []
    for angle in np.linspace(0,360,100):
        cone_vector = angle_offset_vector(boresight_vec, fov_deg / 2, angle)
        cone_vectors.append(cone_vector)
    #Now we have our cone describing the boresight. For each vector, find where it hits the earth.
    intersect_latlongs = []
    for v in cone_vectors:
        #attempt to find an earth intersect
        intersect = find_earth_intersect(sat_pos, v)
        if intersect:
            intersect_latlongs.append(intersect)
    return intersect_latlongs
        
def find_earth_intersect(sat_pos,projected_vector):
    #https://math.stackexchange.com/questions/1939423/calculate-if-vector-intersects-sphere
    #"suppose the line passes through the point P", P is the satellite's location.
    # Since the sphere is centered at C, and that's our origin, we can simplify a bit.
    a = np.dot(projected_vector,projected_vector)
    b = 2 * np.dot(sat_pos,projected_vector)
    c = np.dot(sat_pos,sat_pos) - EARTH_RADIUS*EARTH_RADIUS
    quad_solutions = np.roots([a,b,c])
    # We will get complex solutions if the vector does not intersect the earth. Filter those out.
    real_solutions = [x for x in quad_solutions if not np.iscomplex(x)]
    if len(real_solutions):
        #There are two solutions - one when the vector enters the earth, and one when it exits the other side.
        entry_solution = min(real_solutions)
        entry_location = sat_pos + entry_solution * projected_vector
        _, entry_lat, entry_lon = cart_to_sph(entry_location, toDeg = True)
        return entry_lon,entry_lat
#Given a cartesian vector (X, Y, Z), return a spherical vector(R, lat, long)
#We use a spherical convention where 0 lat is on equator; this differs from some other conventions.
#give toDeg=True to convert to degrees.
def cart_to_sph(cart_in, toDeg = False):
    x,y,z = cart_in
    R = np.linalg.norm(cart_in)
    lat = np.arcsin(z/R)
    lon = np.arctan2(y,x)
    if toDeg:
        lat *= (180/np.pi)
        lon *= (180/np.pi)
    return [R,lat,lon]
#Given a spherical vector(R, lat, lon), return a cartesian vector (X, Y, Z)
def sph_to_cart(sph_in, isDeg = False):
    if isDeg:
        lat = sph_in[1] * np.pi/180
        lon = sph_in[2] * np.pi/180
    else:
        lat = sph_in[1]
        lon = sph_in[2]
    lat = np.pi/2 - lat #handle the change of convention
    R = sph_in[0]
    x = R * np.sin(lat) * np.cos(lon)
    y = R * np.sin(lat) * np.sin(lon)
    z = R * np.cos(lat)
    return [x,y,z]

#Given a cartesian vector (X,Y,Z), return a vector which is offset from that vector, by a particular angle.
#Magnitude = how far the vector is turned, direction = compass direction of that turning.
#Best example: Start with a nadir vector, then generate a vector which is 10 degrees from it, off-nadir toward the southwest.
#magnitude is 10 degrees, direction is 225 degrees.
#Start_vec can be any XYZ vector, magnitude and direction are degrees.
def angle_offset_vector(start_vec, magnitude, direction):
    start_unitvec = start_vec / np.linalg.norm(start_vec)
    start_unitvec_sph = cart_to_sph(start_unitvec, toDeg = True)
    #we now have a spherical unit vector pointing along our start vector.
    #Due to spherical coordinates having consistent latitude angles, we can generate a vector diverted from the start toward the north, by just adding the magnitude to the latitude component.
    north_diverted_sph = [1, start_unitvec_sph[1] + magnitude, start_unitvec_sph[2]]
    north_diverted_cart = sph_to_cart(north_diverted_sph, isDeg = True)
    #Now, to rotate to an arbitrary angle, we can use the axis-angle rotation matrix. We take our diverted vector and revolve it around the initial unit vector.
    #https://en.wikipedia.org/wiki/Rotation_matrix#Rotation_matrix_from_axis_and_angle
    ux, uy, uz = start_unitvec
    angle = direction * np.pi/180 #convert to radians
    #Precalculate the cosine and sine of theta, for the sake of conciseness
    ct = np.cos(angle)
    st = np.sin(angle)
    rot_matrix = np.matrix([[ct + ux*ux*(1-ct),    ux*uy*(1-ct)-uz*st,   ux*uz*(1-ct) + uy*st],
                            [uy*ux*(1-ct) + uz*st, ct+uy*uy*(1-ct),      uy*uz*(1-ct) - ux*st],
                            [uz*ux*(1-ct) - uy*st, uz*uy*(1-ct) + ux*st, ct + uz*uz*(1-ct)]])
    resulting_vector = np.array(np.matmul(rot_matrix, north_diverted_cart)).flatten()
    return resulting_vector

def get_footprint_polygons(center_lat, center_lon, radius):
    #Use the haversine formula, inverted.
    points_left_of_center = []
    points_right_of_center = []
    # generate latitudes which are above and below the center. For each, find the longitude.
    for lat in np.linspace(-HALFPI, HALFPI, 1000): #last arg is the resolution of the circle
        numerator = hav(radius) - hav(lat - center_lat)
        denom = np.cos(center_lat) * np.cos(lat)
        lon_shift = archav( numerator / denom ) #will be None if out of bounds of archav
        if lon_shift is not None:
            points_right_of_center.append([(center_lon + lon_shift + np.pi)%TWOPI-np.pi,lat])
            points_left_of_center.append([(center_lon - lon_shift + np.pi)%TWOPI-np.pi,lat])
    # This will generate points that go clockwise around, going up the left and down the right.
    points_to_plot = [*points_left_of_center, *reversed(points_right_of_center)]
    #append the last one, so that we form a complete closed shape
    points_to_plot.append(points_to_plot[0])

    # If the polygon crosses any of the limits of the map, we get literal edge cases to deal with.
    # This is detectable by comparing our coordinates.
    # but if we aren't near the edge, then put everything in one polygon (arbitrarily, left)
    # We can't cross both 0-longitude and 180-longitude, so if we're closer to 0 (under pi/2)
    # then just build it as one polygon.
    if abs(center_lon) < np.pi/2:
        left_polygon = points_to_plot
        right_polygon = []
    else:
        left_polygon = [p for p in points_to_plot if p[0] < 0]
        right_polygon = [p for p in points_to_plot if p[0] > 0]
    return [left_polygon, right_polygon]