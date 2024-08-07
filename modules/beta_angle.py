from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QPushButton, QAction, QGraphicsEllipseItem, QSlider
import pyqtgraph.opengl as gl
import pyqtgraph as pg
import numpy as np

from skyfield.api import load, EarthSatellite, wgs84, Star, utc
from skyfield.elementslib import osculating_elements_of
from skyfield.framelib import ecliptic_frame
from skyfield.data import hipparcos

def sigmoid_shader(x):
    W = 10#Intensity of the cutoff at 0.5. High = sharp shadow
    return 1/(1+np.exp(-W*(x-0.5)))

class beta_angle():
    def __init__(self,window,initparams):
        #Iterate over everything in initparams.
        for key,value in initparams.items():
            #This does self.key = value, where key is a string.
            setattr(self, key, value)
        self.window = window

        self.view3D = gl.GLViewWidget(self.window)
        self.view3D.setGeometry(0,0,240,240)
        self.view3D.setBackgroundColor('black')

        self.window.grid.addWidget(self.view3D, self.grid_y, self.grid_x, self.grid_h, self.grid_w)

        self.render3DView()
                
        #Expansion button to make the main widget thing
        self.mainwidgetbutton = QPushButton("⛶",self.view3D)
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
        self.update3DView()

    def update3DView(self):
        ts = load.timescale()
        time = ts.from_datetime(self.window.cross_module_vars['globaltime'].replace(tzinfo=utc))

        eph = load('de421.bsp')
        earth_ephemeris = eph['earth']
        earthat = earth_ephemeris.at(time)
        earth_r = earthat.position.km
        earth_v = earthat.velocity.km_per_s

        #Unit vector that points to the earth
        x_hat = earth_r / np.linalg.norm(earth_r)
        #To get the ecliptic north pole, get the angular momentum vector of earth orbit
        earth_h = np.cross(earth_r,earth_v)
        z_hat = earth_h / np.linalg.norm(earth_h)
        #Finally for y. Just z cross x.
        y_hat = np.cross(z_hat,x_hat)
        self.transformation_matrix = np.vstack((x_hat,y_hat,z_hat))

        #Draw the axis of the earth from the north pole to the south pole
        north_pole = wgs84.latlon(90,0).at(time).position.km/1000
        south_pole = wgs84.latlon(-90,0).at(time).position.km/1000
        north_pole = np.dot(self.transformation_matrix,north_pole)
        south_pole = np.dot(self.transformation_matrix,south_pole)

        poles = np.array([north_pole,south_pole])
        
        self.earth_axis.setData(pos=poles)
        self.Nlabel.setData(pos= north_pole)
        self.Slabel.setData(pos= south_pole*1.1)

        equator = [np.dot(self.transformation_matrix,wgs84.latlon(0,lon).at(time).position.km/1000) for lon in range(361)]
        self.equator_drawn.setData(pos=equator)

        for sat in self.drawn_sats:
            sat.update(time)
    def render3DView(self):
        ts = load.timescale()
        time = ts.from_datetime(self.window.cross_module_vars['globaltime'].replace(tzinfo=utc))
        self.oldtime = time
        #This whole 3D plot is done in units of megameters. Therefore earth's radius of 6371km is 6.371 units.

        earth = gl.MeshData.sphere(rows=50, cols=50,radius = 6.371)
        color_map = pg.colormap.get("CET-L15")
        x = earth.vertexes()[:, 0]
        x_max, x_min = x.max(), x.min()
        x_normalized = 1- ((x - x_min) / (x_max-x_min)) #Subtract to 1 to put dark side away from sun
        colors = color_map.map(sigmoid_shader(x_normalized), mode="float")
        earth.setFaceColors(colors)
        self.earthmesh = gl.GLMeshItem(meshdata=earth, smooth=True)
        self.view3D.addItem(self.earthmesh)

        #Determine orientation of the axis using the location of the earth
        eph = load('de421.bsp')
        earth_ephemeris = eph['earth']
        earthat = earth_ephemeris.at(time)
        earth_r = earthat.position.km
        earth_v = earthat.velocity.km_per_s

        #Unit vector that points to the earth
        x_hat = earth_r / np.linalg.norm(earth_r)
        #To get the ecliptic north pole, get the angular momentum vector of earth orbit
        earth_h = np.cross(earth_r,earth_v)
        z_hat = earth_h / np.linalg.norm(earth_h)
        #Finally for y. Just z cross x.
        y_hat = np.cross(z_hat,x_hat)
        self.transformation_matrix = np.vstack((x_hat,y_hat,z_hat))

        #Draw the axis of the earth from the north pole to the south pole
        north_pole = wgs84.latlon(90,0).at(time).position.km/1000
        south_pole = wgs84.latlon(-90,0).at(time).position.km/1000
        north_pole = np.dot(self.transformation_matrix,north_pole)
        south_pole = np.dot(self.transformation_matrix,south_pole)

        poles = np.array([north_pole,south_pole])
        color = np.array([(1,0.6,0,1)]*len(poles))
        self.earth_axis = gl.GLLinePlotItem(pos=poles, color=color, width=5, antialias=True)
        self.view3D.addItem(self.earth_axis)
        #Add text labels for N and S to help orient
        self.Nlabel = gl.GLTextItem(pos= north_pole, text='N',font=QtGui.QFont('Helvetica',10))
        self.Slabel = gl.GLTextItem(pos= south_pole*1.1, text='S',font=QtGui.QFont('Helvetica',10))
        self.view3D.addItem(self.Nlabel)
        self.view3D.addItem(self.Slabel)

        #Draw ring for equator
        equator = [np.dot(self.transformation_matrix,wgs84.latlon(0,lon).at(time).position.km/1000) for lon in range(361)]
        self.equator_drawn = gl.GLLinePlotItem(pos=equator, color=(0.0,1.0,0.0,1.0), width=5, antialias=True)
        self.view3D.addItem(self.equator_drawn)

        #Show the sun much nearer than it should be (at 1500 megameters it's at L1)
        sun_ephemeris = eph['sun']
        sun_vector = (sun_ephemeris - earth_ephemeris).at(time).position.km
        sun_vector = np.dot(self.transformation_matrix,sun_vector)
        self.norm_sun = sun_vector / np.linalg.norm(sun_vector)
        sun = gl.GLScatterPlotItem(pos=self.norm_sun*1500, size=np.array([100]), color=np.array([(1,1,0.1,0.7)]), pxMode=False)
        self.view3D.addItem(sun)

        #Draw a vector pointing to the sun
        self.view3D.addItem(gl.GLLinePlotItem(pos=[[0,0,0],self.norm_sun*10],color=[1,1,1,1], width=5, antialias=False))
        
        #Plot stars, makes it easier to track rotation
        with load.open(hipparcos.URL) as f:
            df = hipparcos.load_dataframe(f)
        df_filtered = df[df['magnitude'] <= 2.5]
        starlist = df_filtered.values.tolist()

        star_positions = []
        star_sizes = []
        for star in starlist:
            mag,ra,dec = star[:3]
            x = np.cos(ra*np.pi/180)
            y = np.sin(ra*np.pi/180)
            z = np.sin(dec*np.pi/180)
            pos = [x,y,z]
            star_positions.append(np.dot(self.transformation_matrix, pos)*10000)
            star_sizes.append((5 - mag)*10)
            
        stars = gl.GLScatterPlotItem(pos=star_positions, size=star_sizes, color=np.array([(1,1,1,1)]*len(star_positions)), pxMode=False)
        self.view3D.addItem(stars)

        self.drawn_sats = []
        #Plot the orbit for one revolution
        for sat in self.SATS:
            sat_obj = rendered_satellite(self,self.view3D,self.window.cross_module_vars['TLES'][sat["ID"]],sat["Color"])
            self.drawn_sats.append(sat_obj)
            show_hide_checkbox = QAction("Show sat: " + str(sat["ID"]),self.window,checkable=True)
            self.window.modulesMenu.addAction(show_hide_checkbox)
            sat_obj.register_checkbox(show_hide_checkbox)

    #Go back to normal size and location when something else becomes the big widget
    def return_to_normal(self):
        self.window.grid.removeWidget(self.view3D)
        self.window.grid.addWidget(self.view3D, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
    def enlarge(self,new_geometry):
        self.window.grid.removeWidget(self.view3D)
        self.window.grid.addWidget(self.view3D, new_geometry[1], new_geometry[0], new_geometry[3], new_geometry[2])
       
class rendered_satellite():
    def __init__(self,parent,GLRenderer,TLE,color):
        self.parent = parent
        self.GLRenderer = GLRenderer
        self.TLE = TLE
        self.orbit_plot = gl.GLLinePlotItem(pos=[], color=color, width=5, antialias=False)
        self.angmom_line = gl.GLLinePlotItem(pos=[], color=color, width=5, antialias=False)
        #Line indicating sun vector projected onto orbital plane
        self.beta_vec = gl.GLLinePlotItem(pos=[], color=color, width=5, antialias=False)

    def update(self,time):
        ts = load.timescale()
        skyfield_sat = EarthSatellite(*self.TLE)
        sat_state = skyfield_sat.at(time)
        sat_period_minutes = osculating_elements_of(sat_state).period_in_days*1440
        one_period = ts.utc(*time.utc[:3],0,range(int(sat_period_minutes)+1))
        positions = np.transpose(skyfield_sat.at(one_period).position.km)/1000
        positions = np.append(positions,positions[:1],0)#Make it a ring
        ecliptic_positions = [np.dot(self.parent.transformation_matrix,p) for p in positions]
        self.orbit_plot.setData(pos=ecliptic_positions)

        pos = np.dot(self.parent.transformation_matrix,sat_state.position.km)
        vel = np.dot(self.parent.transformation_matrix,sat_state.velocity.km_per_s)
        angmom = np.cross(pos,vel)
        angmom = angmom / np.linalg.norm(angmom)
        self.angmom_line.setData(pos=[[0,0,0],angmom*10])
        
        projected_vector = self.parent.norm_sun - (angmom * np.dot(self.parent.norm_sun,angmom))
        self.beta_vec.setData(pos=[[0,0,0],projected_vector*10])
    def register_checkbox(self,checkbox):
        checkbox.triggered.connect(lambda: self.toggleVisible(checkbox.isChecked()))
    def toggleVisible(self, vis_state):
        if vis_state:
            self.GLRenderer.addItem(self.orbit_plot)
            self.GLRenderer.addItem(self.angmom_line)
            self.GLRenderer.addItem(self.beta_vec)
        else:
            self.GLRenderer.removeItem(self.orbit_plot)
            self.GLRenderer.removeItem(self.angmom_line)
            self.GLRenderer.removeItem(self.beta_vec)
