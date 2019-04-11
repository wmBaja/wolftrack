#!/usr/bin/python3

from PyQt5.QtCore import pyqtSignal
from SensorPoller import SensorPoller

# import os to check if the machine is a RPI
import os
machineIsRaspberryPi = os.uname()[4].startswith("arm")

# if running on a RPI
if (machineIsRaspberryPi):
    # import libraries related to reading from the GPIO of the RPI
    import busio
    import digitalio
    import board
    import adafruit_mcp3xxx.mcp3008 as MCP
    from adafruit_mcp3xxx.analog_in import AnalogIn

    # this is the pin on the MCP3008 that is connected to the hall sensor
    # on the fuel tank
    FUEL_HALL_SENSOR_MCP_PIN = MCP.P0
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
            print("DO SET UP FOR GPS")
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
        voltage = 1
        # if running on a RPI
        if (machineIsRaspberryPi):
            # TODO get the data from the GPS
            print("GET THE DATAS FROM THE GPS")
        else:
            # TODO just get the next value from the mock data
            print("GET THE MOCK DATAS")
