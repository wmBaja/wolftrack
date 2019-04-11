#!/usr/bin/python3

"""
This is the main entry point for the WolfTrack application.  This file also
contains the code for the WolfTrack class which serves as the model of the
application.  When run, this file will start a PyQt QApplication, initialize
the model, and connect it with the view.

Author: Stanton Parham
"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal, QDateTime, Qt
import sys
from MainWindow import MainWindow

# import pollers
from FuelPoller import FuelPoller
from GPSPoller import GPSPoller

# the number of milliseconds in between speed calculations
GPS_POLLING_RATE = 200
# the number of milliseconds in between fuel level calculations
FUEL_POLLING_RATE = 1000

class WolfTrack(QObject):
    """
    This is the model of the WolfTrack application.  It maintains all of the
    state and handles polling to various pieces of hardware.
    """
    # signal emitted when there is a change in gps data
    gpsChange = pyqtSignal(float, float, float, float)
    # signal emitted when there is a change in the fuel level
    fuelChange = pyqtSignal(float, float, float)

    def __init__(self):
        super().__init__()
        print('Initializing WolfTrack...')

        # GPS
        self.gpsPoller = GPSPoller(GPS_POLLING_RATE)
        self.gpsPoller.signal.connect(self.gpsChange)
        self.gpsPoller.start()

        # fuel
        self.fuelPoller = FuelPoller(FUEL_POLLING_RATE)
        self.fuelPoller.signal.connect(self.fuelChange)
        self.fuelPoller.start()

        now = QDateTime.currentDateTime()
        datestr = now.toUTC().toString(Qt.ISODate)
        # save fuel data
        fuel_filename = datestr + "_fuel_data.txt"
        self.fuel_file = open("data/" + fuel_filename, "a+")
        self.fuelChange.connect(self.saveFuelData)
        # save GPS data
        gps_filename = datestr + "_gps_data.txt"
        self.gps_file = open("data/" + gps_filename, "a+")
        self.gpsChange.connect(self.saveGPSData)

    def quit(self):
        print('Cleaning up and exiting...')
        self.fuel_file.close()
        self.gps_file.close()
        sys.exit(0)

    def saveFuelData(self, fuelPerc, fuelLiters, emaLiters):
        now = QDateTime.currentDateTime()
        utc = now.toUTC().toString(Qt.ISODate)

        self.fuel_file.write("{:s},{:.2f},{:.2f}\n".format(utc, fuelLiters, emaLiters))
        # self.fuel_file.write("{:.2f}\n".format(emaLiters))

    def saveGPSData(self, lat, lon, speed, trackAngle):
        now = QDateTime.currentDateTime()
        utc = now.toUTC().toString(Qt.ISODate)

        self.gps_file.write("{:s},{:.6f},{:.6f},{:.2f},{:.2f}\n".format(utc, lat, lon, speed, trackAngle))

if __name__ == '__main__':
    # this has to be initialized before anything that uses Qt
    app = QApplication(sys.argv)
    model = WolfTrack()
    view = MainWindow(model)
    view.showFullScreen()
    # view.show()
    sys.exit(app.exec_())
