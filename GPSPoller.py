#!/usr/bin/python3

from PyQt5.QtCore import pyqtSignal
from SensorPoller import SensorPoller

# import os to check if the machine is a RPI
import os
machineIsRaspberryPi = os.uname()[4].startswith("arm")

# if running on a RPI
if (machineIsRaspberryPi):
    # import libraries related to reading from the GPS module
    import busio
    import board
    import time
    import adafruit_gps
else:
    import random


# the lowest voltage value given by the hall sensor
LOWEST_VOLTAGE = 0.05

# the middle voltage given by the hall sensor
# This is the voltage when no magnetic field is being experienced by the
# hall sensor.
MIDDLE_VOLTAGE = 1.00

# the highest voltage value given by the hall sensor
HIGHEST_VOLTAGE = 2.01

# the maximum number of liters of fuel that the tank can hold
MAX_FUEL_CAPACITY = 3.45
# the maximum number of liters of fuel that the hall sensor can detect
MAX_DETECTED_FUEL_CAPACITY = 1.6

# the weight of each successive fuel calculation
EMA_WEIGHT = 0.1

# the file name for a file of mocked voltages for the fuel
MOCKED_FUEL_DATA_FILE_NAME = "mock_voltages.txt"


class GPSPoller(SensorPoller):
    """
    This object serves as an independent thread that polls for GPS data.
    """
    # signal that emits latitude, longitude, and speed
    signal = pyqtSignal(float, float, float, float)
    # the current latitude
    latitude = 0.0
    # the current longitude
    longitude = 0.0
    # the current speed
    speed = 0.0
    # the current track track angle
    trackAngleDeg = 0.0

    def __init__(self, pollingRate):
        super().__init__(pollingRate / 2 - 5) # have to poll at least as twice as fast as the interval that you want data at
        # if running on a RPI
        if (machineIsRaspberryPi):
            # TODO do set up for GPS
            # for a computer, use the pyserial library for uart access
            import serial
            uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=3000)

            # Create a GPS module instance.
            self.gps = adafruit_gps.GPS(uart, debug=False)
            self.gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0') # set data that you want
            self.gps.send_command(b('PMTK220,' + str(pollingRate))) # set polling rate
        else:
            # TODO find a way to mock data
            print("DO SET UP FOR MOCK DATA")

    def poll(self):
        # get the GPS data from the module
        self.getGPSData()
        # emit the info
        self.signal.emit(self.latitude, self.longitude, self.speed, self.trackAngleDeg)

    def getGPSData(self):
        """
        Gets the GPS data from the module.
        """
        # if running on a RPI
        if (machineIsRaspberryPi):
            # get the data from the GPS
            self.gps.update()
            if not gps.has_fix:
                # Try again if we don't have a fix yet.
                print('Waiting for fix...')
            else:
                # get the lat and lon
                self.latitude = gps.latitude
                self.longitude = gps.longitude
                if gps.speed_knots is not None:
                    # get the speed in MPH
                    self.speed = gps.speed_knots * 1.151
                if gps.track_angle_deg is not None:
                    # get the tracking angle
                   self.trackAngleDeg = gps.track_angle_deg
        else:
            # TODO just get the next value from the mock data
            print("GET THE MOCK DATAS")
