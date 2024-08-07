# Creates a "virtual" satellite, one that we can model in
# the simulation but which is not real. We set it to follow
# a leader satellite. It is either a given number of minutes
# or a given number of kilometers behind the leader.
# This module does not exist as a tile in the main GUI, but is in the menu bar.

# Note that the method used to create the follower may not be robust to all circumstances,
# especially in eccentric orbits.

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QAction, QDialog, QGridLayout, QLabel, QComboBox, QSpinBox
import pyqtgraph as pg
import numpy as np

earth_mu = 3.986e14

def get_TLE_period(tle_in):
    # Get the period from the given mean motion.
    tle_mean_motion = float(tle_in[1][52:63])
    # that's in orbits per day. 86400 seconds per day means we can get seconds per orbit.
    return 86400 / tle_mean_motion
# Assuming a circular orbit, convert the TLE period to a velocity.
def get_TLE_velocity(tle_in):
    period = get_TLE_period(tle_in)
    # v = 2pi * a / T. So we need a. Standard formula.
    SMA = np.cbrt(earth_mu * period**2 / (4*np.pi**2)) # in meters
    velocity = 2 * np.pi * SMA / period
    return velocity

class follower_sat():
    def __init__(self,window,initparams):
        #Iterate over everything in initparams.
        for key,value in initparams.items():
            #This does self.key = value, where key is a string.
            setattr(self, key, value)
        self.window = window
        #initialize follower's TLE to match leader's
        leader_tle = self.window.cross_module_vars['TLES'][self.leader_ID]
        self.window.cross_module_vars['TLES'][self.sat_ID] = leader_tle

        #Initialize following to 0 (right on the leader)
        self.separation_time = 0
        #need velocity to convert between distances and times
        self.leader_velocity = get_TLE_velocity(leader_tle)

        #Now generate the UI. This module supports two different forms of UI.

        # UI form 1: A module visible in the window, like most modules
        # Check for this by testing if we have a defined color.
        self.moduleMode = False
        if "color" in initparams:
            self.moduleMode = True
            self.box = pg.GraphicsLayoutWidget(window)
            self.window.grid.addWidget(self.box, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
            self.box.setStyleSheet("border:2px solid black; border-radius: 5px;")
            self.box.setBackground(self.color)
            self.control_layout(parent=self.box)
        
        # UI form 2: A pop-up window that is spawned from an option in the menu bar
        sat_control_button = QAction("Show follower control panel", self.window)
        self.window.modulesMenu.addAction(sat_control_button)
        sat_control_button.triggered.connect(lambda: self.show_controls())

    def recalculate_TLE(self):
        leader_tle = self.window.cross_module_vars['TLES'][self.leader_ID]
        # Follower's TLE will be just like the leader's, but in order to follow, we change
        # the mean anomaly. To know the difference in mean anomaly, we need the
        # period of the orbit, since fraction of period is equal to mean anomaly fraction of 360.
        leader_period = get_TLE_period(leader_tle)
        # Now we know the time, convert to orbit fraction.
        orb_time_fraction = self.separation_time / leader_period
        mean_anomaly_diff = orb_time_fraction * 360
        # Now generate the new TLE. Use the old one, just subbing in the ID and new mean anomaly.
        old_mean_anomaly = float(leader_tle[1][43:51])
        new_mean_anomaly = old_mean_anomaly - mean_anomaly_diff
        if new_mean_anomaly < 0:
            new_mean_anomaly += 360
        #start by copying old TLE into a list of characters (lists are mutable)
        new_tle = [list(x) for x in leader_tle]
        new_tle[1][43:51] = list(f'{new_mean_anomaly:.4f}')
        #convert back to a list of 2 strings
        new_tle = ["".join(x) for x in new_tle]
        #Give that TLE to the window for other modules to use. self.sat_ID comes from config file!
        self.window.cross_module_vars['TLES'][self.sat_ID] = new_tle
    # Get a QGridLayout holding all the UI elements for this module
    def control_layout(self, parent=None):
        if self.moduleMode:
            fontsize = 30 # Would be nice if this could auto-adapt to fit. Works for now.
        else:
            fontsize = 24
        font = QFont("Helvetica",fontsize)
        grid = QGridLayout(parent)
        #Block for controlling time
        self.timeInputLabel = QLabel(" Time separation (s):")
        self.timeInputLabel.setFont(font)
        grid.addWidget(self.timeInputLabel,0,0)
        self.timeInput = QSpinBox()
        self.timeInput.setValue(int(self.separation_time))
        self.timeInput.setMaximum(9999)
        self.timeInput.setFont(font)
        grid.addWidget(self.timeInput,0,1)
        self.timeInput.valueChanged.connect(self.timeChange)
        #Block for controlling distance
        self.distInputLabel = QLabel("Dist separation (km):")
        self.distInputLabel.setFont(font)
        grid.addWidget(self.distInputLabel,1,0)
        self.distInput = QSpinBox()
        self.distInput.setValue(int(self.separation_time * self.leader_velocity / 1000))
        self.distInput.setMaximum(9999)
        self.distInput.setFont(font)
        grid.addWidget(self.distInput,1,1)
        self.distInput.valueChanged.connect(self.distChange)
        return grid

    def timeChange(self, newTime):
        # calculate the distance to apply to the other field.
        newDist = newTime * self.leader_velocity/1000
        #block the signals for the distInput to avoid an infinite loop setting each other
        self.distInput.blockSignals(True)
        self.distInput.setValue(int(newDist))
        self.distInput.blockSignals(False)
        self.separation_time = newTime
        self.recalculate_TLE()
    def distChange(self, newDist):
        newTime = newDist*1000 / self.leader_velocity
        self.timeInput.blockSignals(True)
        self.timeInput.setValue(int(newTime))
        self.timeInput.blockSignals(False)
        self.separation_time = newTime
        self.recalculate_TLE()
    # If operating in non-visible module mode
    def show_controls(self):
        parent_module = self
        class FollowerControlDialog(QDialog):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("Follower satellite control")
                self.setWindowModality(False) #enables interacting with main window even while dialog is up
                #populate UI elements
                grid = parent_module.control_layout()
                self.setLayout(grid)
                parent_module.recalculate_TLE()
            
            
        settingsWindow = FollowerControlDialog()
        settingsWindow.exec()
    def export_data(self):
        data_out = {}
        data_out["separation_time"] = self.separation_time
        return data_out

    
