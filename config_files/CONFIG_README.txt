Configuration files should be json files holding all the modules of the configuration.

At the top level of the file should be the following lines:

{
"modules":[

This starts a dictionary, where the first key is "modules", which gives a list of all the modules.

Each module is itself a dictionary, where each entry is the name and value of a parameter for that module.

A module can have any parameters you want, but all must have the following:

    "name": A name you'll use to describe this module in your configuration. This should be unique in the configuration. If you have multiple BlueCircle modules in your configuration, they should be named BlueCircle1, BlueCircle2, etc.
    "source_file": The name of the Python file in the /modules directory, which holds a class matching your className. Do not include the .py file extension, only the main name.
    "initparams": A dictionary of values that will be passed to construct this object. It should always have, at minimum, an xpos, ypos, width, and height.
