from PyQt5.QtWidgets import QPushButton, QLabel, QSizePolicy
from PyQt5.QtGui import QPixmap
import pyqtgraph as pg

import urllib

class space_weather_embed():
    def __init__(self,window,initparams):
        #Iterate over everything in initparams.
        for key,value in initparams.items():
            #This does self.key = value, where key is a string.
            setattr(self, key, value)

        self.window = window
        
        image_url = "https://services.swpc.noaa.gov/images/notifications-timeline.png"
        image_bytes = urllib.request.urlopen(image_url).read()

        self.image_holder = QLabel(self.window)
        self.pixmap = QPixmap()
        self.pixmap.loadFromData(image_bytes)
        self.image_holder.setScaledContents(True)
        self.image_holder.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_holder.setPixmap(self.pixmap)

        self.window.grid.addWidget(self.image_holder, self.grid_y, self.grid_x, self.grid_h, self.grid_w)

        #Expansion button to make the main widget thing
        self.mainwidgetbutton = QPushButton("⛶",self.image_holder)
        self.mainwidgetbutton.resize(30, 30)
        self.mainwidgetbutton.move(10,0)
        self.mainwidgetbutton.setStyleSheet("background-color:#bbbbbb")
        self.mainwidgetbutton.clicked.connect(lambda:self.window.set_largeCentralPanel(self))
    #Go back to normal size and location when something else becomes the big widget
    def return_to_normal(self):
        self.window.grid.removeWidget(self.image_holder)
        self.window.grid.addWidget(self.image_holder, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
    def enlarge(self,new_geometry):
        self.window.grid.removeWidget(self.image_holder)
        self.window.grid.addWidget(self.image_holder, new_geometry[1], new_geometry[0], new_geometry[3], new_geometry[2])
