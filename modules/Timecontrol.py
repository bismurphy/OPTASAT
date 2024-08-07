from PyQt5 import QtCore
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QPushButton,QDateTimeEdit, QLabel, QGridLayout, QSizePolicy
import pyqtgraph as pg
import datetime

class Timecontrol():
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

        grid = QGridLayout(self.box)

        self.title = QLabel(self.box)
        self.title.setText("Time Controller")
        self.title.setAlignment(QtCore.Qt.AlignCenter)
        self.title.setStyleSheet("border:0px")
        self.title.setFont(QFont("Helvetica",18))
        grid.addWidget(self.title, 0, 0, 1, 4) # let the title bar span all 4 columns
        self.title.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)

        self.dateTimeEdit = QDateTimeEdit(self.box)
        self.dateTimeEdit.setWrapping(True) # allow the text to go 2 lines if needed
        self.dateTimeEdit.setDisplayFormat("yyyy-MM-dd hh:mm:ss")
        self.dateTimeEdit.dateTimeChanged.connect(lambda:self.set_time(self.dateTimeEdit.dateTime().toPyDateTime()))
        self.window.cross_module_vars['globaltime'] = datetime.datetime.utcnow()
        grid.addWidget(self.dateTimeEdit,1,0,1,2)
        self.dateTimeEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)


        self.paused = False
        self.pauseButton = QPushButton("Pause Time", self.box)
        self.pauseButton.clicked.connect(self.toggle_pause)
        grid.addWidget(self.pauseButton,1,2)
        self.pauseButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)


        self.nowButton = QPushButton("Set Time to Now", self.box)
        self.nowButton.clicked.connect(self.set_time_now)
        grid.addWidget(self.nowButton,1,3)
        self.nowButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        
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
    def toggle_pause(self):
        self.paused = not self.paused
        self.pauseButton.setText("Unpause" if self.paused else "Pause Time")
    def set_time(self, new_datetime):
        self.window.cross_module_vars['globaltime'] = new_datetime
    def set_time_now(self):
        self.dateTimeEdit.setDateTime(datetime.datetime.utcnow())
    def update(self):
        if not self.paused:
            self.dateTimeEdit.setDateTime(self.window.cross_module_vars['globaltime']+ datetime.timedelta(seconds=1))
    def export_data(self):
        return {"Name":self.name}
    #Go back to normal size and location when something else becomes the big widget
    def return_to_normal(self):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, self.grid_y, self.grid_x, self.grid_h, self.grid_w)
    def enlarge(self,new_geometry):
        self.window.grid.removeWidget(self.box)
        self.window.grid.addWidget(self.box, new_geometry[1], new_geometry[0], new_geometry[3], new_geometry[2])
    
