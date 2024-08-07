from PyQt5.QtWidgets import QPushButton, QVBoxLayout
import pyqtgraph as pg

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas

from skyfield.api import load,EarthSatellite,wgs84

tracking_days = 14

class passfinder():
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

        self.fig, self.ax = plt.subplots()
        # Invert Y axis, so time flows down, like a Google Calendar
        self.ax.set_ylim(self.ax.get_ylim()[::-1])
        self.plotWidget = FigureCanvas(self.fig)

        #Create a plot holder and place the plot inside of it
        self.plotHolder = QVBoxLayout(self.box)
        self.plotHolder.setContentsMargins(10, 10, 10, 10)      
        self.plotHolder.addWidget(self.plotWidget)

        #Load in all ground stations registered to the window
        gs_data = self.window.params['Groundstations']
        for gs in gs_data:
            #Filter for the one matching the name we're seeking
            if gs['Name'] == self.groundstation:
                self.gs_data = gs
                break
        
        self.TLE = self.window.cross_module_vars['TLES'][self.sat_id]
        self.plot_passes()

        #Expansion button to make the main widget thing
        self.mainwidgetbutton = QPushButton("⛶",self.box)
        self.mainwidgetbutton.resize(30, 30)
        self.mainwidgetbutton.move(10,0)
        self.mainwidgetbutton.setStyleSheet("background-color:#bbbbbb")
        self.mainwidgetbutton.clicked.connect(lambda:self.window.set_largeCentralPanel(self))
    def plot_passes(self):
        #color-code passes using the autumn color map
        cmap = plt.get_cmap('autumn')
        self.passes = self.get_passes()
        starts = [p["start"] for p in self.passes]
        maxels = [p["max_el"] for p in self.passes]
        #Split the date and time of each of the starts. We plot x as date and y as time.
        pass_dates = [] #day
        pass_tods = []  #time of day
        for start_time in starts:
            start_date = "/".join(str(x) for x in [start_time.utc.year,start_time.utc.month,start_time.utc.day])
            #normalize the time into decimal hours
            start_hours = start_time.utc.hour + (start_time.utc.minute + (start_time.utc.second)/60)/60
            pass_dates.append(start_date)
            pass_tods.append(start_hours)
        #Plot the points! Color them based on their maximum elevation, and size them the same way.
        colors = [cmap(m/90) for m in maxels]
        self.scatter = plt.scatter(pass_dates, pass_tods, c = colors, s=[a**2/7 for a in maxels])
        #Plot all the numbers inside their circles. Center the marks on their points and size to fit.
        for i,n in enumerate(maxels):
            plt.annotate(int(n), (pass_dates[i],pass_tods[i]),ha='center',va='center',c="black",weight='bold',size=n/4)

        #These will give passes labels on mouseover
        self.annot = self.ax.annotate("", xy=(0,0), xytext=(20,20),textcoords="offset points",
                    bbox=dict(boxstyle="round", fc="w"),
                    arrowprops=dict(arrowstyle="->",color='w'))
        self.annot.set_visible(False)
        self.fig.canvas.mpl_connect("motion_notify_event", self.hover)
        self.fig.canvas.mpl_connect("button_press_event", self.click)
        
        #Rotate dates sideways so they all fit
        plt.xticks(rotation=90)
        plt.yticks(list(range(25)),labels = [str(i) + ":00" for i in range(25)]) 
        plt.title("GS: " + self.groundstation)
        plt.ylabel("Time of day (UTC)")

        #Draw the vertical lines between dates for ease of viewing dates of the top passes
        for xc in [0.5 + i for i in range(tracking_days)]:
            plt.axvline(x=xc, color='k', linestyle='--')
        self.ax.set_transform(self.ax.transData)
    #Standard Skyfield code for getting passes.
    #Generate a list of passes with start times, end times, and max-elevations.
    def get_passes(self):
        ts = load.timescale()
        start_time = ts.now()
        end_time = ts.tt_jd(start_time.tt + tracking_days)
        satellite = EarthSatellite(*self.TLE)
        skyfield_groundstation = wgs84.latlon(self.gs_data["Lat"],self.gs_data["Lon"])
        times, events = satellite.find_events(skyfield_groundstation, start_time,end_time)
        passes = []
        curr_pass = {}
        for t, event_type in zip(times,events):
            if event_type == 0:
                curr_pass = {"start":t}
            if event_type == 1: # this is the moment of maximum elevation; calculate that value.
                if "start" not in curr_pass:
                    continue
                max_el = (satellite - skyfield_groundstation).at(t).altaz()[0].degrees
                curr_pass["max_el"] = max_el
            if event_type == 2:
                if "start" not in curr_pass:
                    continue
                curr_pass["end"] = t
                if all(x in curr_pass for x in ["start","max_el"]):
                    passes.append(curr_pass)
        return passes
    def update_annot(self,ind):
        pos = self.scatter.get_offsets()[ind["ind"][0]]
        self.annot.xy = pos
        pass_to_label = self.passes[ind["ind"][0]]
        text = pass_to_label["start"].utc_strftime()
        self.annot.set_text(text)

    def hover(self,event):
        vis = self.annot.get_visible()
        if event.inaxes == self.ax:
            cont, ind = self.scatter.contains(event)
            if cont:
                self.update_annot(ind)
                self.annot.set_visible(True)
                self.fig.canvas.draw_idle()
            else:
                if vis:
                    self.annot.set_visible(False)
    #Respond to clicking on a point in the scatterplot
    def click(self,event):
        if event.inaxes == self.ax:
            cont, ind = self.scatter.contains(event)
            if cont:
                self.clicked_pass = self.passes[ind["ind"][0]]
                selected_time = self.clicked_pass["start"].utc_datetime()
                #Convert to a Python datetime and jump globaltime to that time
                self.window.cross_module_vars['globaltime'] = selected_time
    # Convert the Skyfield times in a pass to human readable UTC times
    def export_pass(self, p):
        exported_pass = {}
        exported_pass['start'] = p['start'].utc_datetime()
        exported_pass['max_el'] = p['max_el']
        exported_pass['end'] = p['end'].utc_datetime()
        return exported_pass
    def export_data(self):
        data_out = {}
        data_out["Chosen_pass"] = self.export_pass(self.clicked_pass)
        data_out["All_passes"] = [self.export_pass(p) for p in self.passes]
        return data_out
    #Go back to normal size and location when something else becomes the big widget
    def return_to_normal(self):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
    def enlarge(self,new_geometry):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, new_geometry[1], new_geometry[0], new_geometry[3], new_geometry[2])