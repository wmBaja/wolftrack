#!/usr/bin/python3

"""
This is the main entry point for the WolfTrack application.  This file also
contains the code for the WolfTrack class which serves as the model of the
application.  When run, this file will start a PyQt QApplication, initialize
the model, and connect it with the view.

Author: Stanton Parham
"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal
import sys
from MainWindow import MainWindow

# import pollers
from SpeedPoller import SpeedPoller
from FuelPoller import FuelPoller

# the number of milliseconds in between speed calculations
SPEED_POLLING_RATE = 100
# the number of milliseconds in between fuel level calculations
FUEL_POLLING_RATE = 1000

class WolfTrack(QObject):
    """
    This is the model of the WolfTrack application.  It maintains all of the
    state and handles polling to various pieces of hardware.
    """
    # signal emitted when there is a change in speed
    speedChange = pyqtSignal(int)
    # signal emitted when there is a change in RPMs
    rpmChange = pyqtSignal(int)
    # signal emitted when there is a change in the fuel level
    fuelChange = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        print('Initializing WolfTrack...')

        # speed
        self.speedPoller = SpeedPoller(SPEED_POLLING_RATE)
        self.speedPoller.signal.connect(self.speedChange)
        self.speedPoller.start()

        # fuel
        self.fuelPoller = FuelPoller(FUEL_POLLING_RATE)
        self.fuelPoller.signal.connect(self.fuelChange)
        self.fuelPoller.start()

    def quit(self):
        print('Cleaning up and exiting...')
        sys.exit(0)


if __name__ == '__main__':
    # this has to be initialized before anything that uses Qt
    app = QApplication(sys.argv)
    model = WolfTrack()
    view = MainWindow(model)
    # view.showFullScreen()
    view.show()
    sys.exit(app.exec_())
