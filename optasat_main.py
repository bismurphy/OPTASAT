import sys
import json
#Allows importing a file by name, as specified in config
import importlib
#Custom script for grabbing TLE updates
import load_tle

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QGridLayout, QFileDialog

#Less-known publications which could be good to publish in:
#Journal of space operations, air and space operations review, space mission planning and operations
#Some IEEE journals, OPS-SAT stuff, Space mission planning and operations

from PyQt5.QtWidgets import QMainWindow, QMenuBar, QMenu, QAction, QWidget
import datetime

#The window class that holds everything.
class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OPTASAT")
        self.grid = QGridLayout()
        # QMainWindow has a Central Widget, that will hold our main layout which has all modules
        self.widget_holder = QWidget()
        self.widget_holder.setLayout(self.grid)
        self.setCentralWidget(self.widget_holder)
    
        self.menubar = QMenuBar(self)
        
        self.fileMenu = QMenu("File", self)
        self.modulesMenu = QMenu("Modules", self)

        self.menubar = QMenuBar(self)
        self.menubar.addMenu(self.fileMenu)
        self.menubar.addMenu(self.modulesMenu)

        loadConfigButton = QAction("Load Configuration",self)
        self.fileMenu.addAction(loadConfigButton)
        loadConfigButton.triggered.connect(self.load_config)

        dataExportButton = QAction("Export Module State Data",self)
        self.fileMenu.addAction(dataExportButton)
        dataExportButton.triggered.connect(self.export_module_data)

        quitButton = QAction("Quit",self)
        self.fileMenu.addAction(quitButton)
        quitButton.triggered.connect(self.close)

        #A dictionary that any module can read or write to, in order to exchange data between each other.
        self.cross_module_vars = {}
    def load_config(self):
        print("Loading configuration")
        chosen_config_file = QFileDialog.getOpenFileName(self)[0]
        self.params=None
        with open(chosen_config_file, encoding='utf-8') as f:
            self.params = json.load(f)
        TLES = {x : load_tle.get_tle(x) for x in self.params['Spacecraft_IDS']}
        self.cross_module_vars["TLES"] = TLES
        # Initialize global time to now, other modules (especially time controller) may change it.
        if "start_time" in self.params:
            self.cross_module_vars['globaltime'] = datetime.datetime(*self.params['start_time'])
        else:
            self.cross_module_vars['globaltime'] = datetime.datetime.utcnow()

        self.all_active_modules = []
        for module in self.params['modules']:
            file = module['source_file']
            importname = "modules." + file
            imported_module = importlib.import_module(importname)
            #Get the class by name, which should be identical to the filename.
            #Split on dot and get last one, for end of file path.
            module_class = getattr(imported_module,file.split(".")[-1])
            module_instance = module_class(self,module['initparams'])
            self.all_active_modules.append(module_instance)
        # Modules made, now some final geometry work
        self.centralGeometry = self.params['central_geometry']
        self.largeCentralPanel = None
        # Make the grid layout share rows and columns evenly
        min_height = self.centralGeometry[1] + self.centralGeometry[3]
        min_width = self.centralGeometry[0] + self.centralGeometry[2]
        for i in range(max(min_height,self.grid.rowCount())):
            self.grid.setRowStretch(i, 1)
        for j in range(max(min_width,self.grid.columnCount())):
            self.grid.setColumnStretch(j, 1)
        main_window.hide()
        main_window.show()
    # When the "Export Module state data" button is pressed in the File menu,
    # we iterate over every module in the current configuration. For each one,
    # check if it has a function called "export_data". If it does, call that function.
    # export_data must export a dictionary of all the relevant data to be exported,
    # which will be different from function to function. We then take all those
    # dictionaries, and output them as a single JSON file to be saved to the
    # hard drive. The user is prompted with where to save it.
    def export_module_data(self):
        data_dump_dict = {"Cross module vars":self.cross_module_vars}
        for module in self.all_active_modules:
            print(module.name)
            print("export_data" in dir(module))
            if("export_data" in dir(module)):
                exported_data = module.export_data()
                data_dump_dict[module.name] = exported_data
        #Data is dumped to a dictionary, now write it out as JSON
        default_file_path = __file__
        savefile, _ = QFileDialog.getSaveFileName(self,"Save File",default_file_path,"All Files(*)")
        if savefile:
            with open(savefile, "w") as f:
                json.dump(data_dump_dict, f, indent=4, default=str)
    def set_largeCentralPanel(self,newCenterWidget):
        if self.largeCentralPanel is not None:
            self.largeCentralPanel.return_to_normal()
        self.largeCentralPanel = newCenterWidget
        self.largeCentralPanel.enlarge(self.centralGeometry)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = Window()
    main_window.load_config()
    main_window.showMaximized()
    sys.exit(app.exec_())
