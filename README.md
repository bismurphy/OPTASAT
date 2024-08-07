# OPTASAT

OPTASAT (Open-source Python Tool for Awareness of Spacecraft and Analysis of Telemetry) is a toolkit intended for operators of small satellites to understand the status of their spacecraft and the geometry of its orbital conditions, with an emphasis on visualizing data in useful, easy-to-understand ways.

OPTASAT is fully open-source, and 100% of its code is written in Python, enabling operators to modify the code as they please. Additionally, because Python is cross-platform, OPTASAT is cross-platform. Users have successfully run OPTASAT on Linux, Windows, and Mac systems. Development is primarily done on Linux but all platforms are intended to be supported, and will have bugs fixed if reported.

OPTASAT is module-based. When running OPTASAT, the user is prompted to choose a configuration file to control the graphical interface. This repository comes with several examples in the `config_files` directory. After selecting a configuration, the user will see a window, with several rectangular modules placed around. Each of these modules is controlled by a single Python script. The main script, `optasat_main.py`, controls all the other modules. When starting OPTASAT, the user selects a JSON file, which contains all the configuration options to control their OPTASAT scenario. This includes functional options (such as the choice of which satellites are being tracked, or the coordinates of a user's ground station), as well as graphical options (defining the physical location of each module in the window). This way, a user can create their own layouts with their own parameters, without needing to directly modify any code.

I recommend installing the software using the instructions below, then, after running it, select `config_files/test_config.json` to get a quick view of an example OPTASAT layout. `config_files/multimission_demo/click_following.json` also gives a nice real-world use case for OPTASAT in analyzing the behavior of a pair of satellites with respect to the location of a ground station.

# Installation
OPTASAT does not "install" natively onto a user's computer; all of its files are stored within its own directory. In order to run OPTASAT, perform the following:

1. Install Python. This may not be necessary depending on your system.
2. Download the code. You can either clone this repository, or simply download the ZIP.
3. Install the required Python libraries. The easiest way to do this is to `cd` to the OPTASAT directory, and then run `pip3 install -r requirements.txt`, which will install all the libraries listed in the repository's requirements.txt file.
4. Run `optasat_main.py`. You will be prompted to select a configuration file. Several are provided in the `config_files` directory, and you are encouraged to use these files as inspiration to create your own.
  * Note: If you get an error about "Could not load the Qt platform plugin `xcb`", try `sudo apt-get install libxcb-xinerama0`

# Final Notes
OPTASAT was developed in the process of my PhD. It is still in its early days, but there is enough here to be useful. Any and all feedback is hugely appreciated. So far, I've mostly been just imagining what features would be useful to have, or what interfaces would be intuitive, but if anyone has other thoughts, I would love to hear them. If you have used OPTASAT for even the simplest of tasks, that would also be amazing to hear. OPTASAT is under active development and is very open to input from anyone who would like to contribute code.

Please feel free to start a discussion in the Discussions tab of this repository if you have any questions about OPTASAT. Thank you for your interest!
