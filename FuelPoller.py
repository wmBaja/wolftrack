#!/usr/bin/python3

from PyQt5.QtCore import pyqtSignal
from SensorPoller import SensorPoller

import math

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


class FuelPoller(SensorPoller):
    """
    This object serves as an independent thread that polls for a fuel level.
    """
    # signal that emits the current fuel level as a float (between 0.0 and 1.0)
    signal = pyqtSignal(float, float, float)
    # the percentage (as a value between 0.0 and 1.0) of fuel remaining
    remainingPerc = 0
    # the raw liters of remaining fuel
    remainingLiters = MAX_DETECTED_FUEL_CAPACITY
    # the liters of remaining fuel based on an exponential moving average
    emaLiters = MAX_DETECTED_FUEL_CAPACITY

    def __init__(self, pollingRate):
        super().__init__(pollingRate)
        # if running on a RPI
        if (machineIsRaspberryPi):
            # create the spi bus
            spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
            # create the cs (chip select)
            cs = digitalio.DigitalInOut(board.D5)
            # create the mcp object
            mcp = MCP.MCP3008(spi, cs)
            # create an analog input channel on pin 0
            self.sensorChannel = AnalogIn(mcp, FUEL_HALL_SENSOR_MCP_PIN)
        else:
            # read in mock values from a file
            with open(MOCKED_FUEL_DATA_FILE_NAME) as file:
                lines = file.readlines()
                self.mocked_data = [float(val) for val in lines]
                self.mocked_data_idx = 0

    def poll(self):
        # calculate the remaining fuel
        self.calculateRemainingFuel()
        # emit fuel percentage value
        self.signal.emit(self.remainingPerc, self.remainingLiters, self.emaLiters)

    def calculateRemainingFuel(self):
        """
        Calculates the remaining fuel in the tank based on a voltage value.
        """
        voltage = 1
        # if running on a RPI
        if (machineIsRaspberryPi):
            voltage = self.sensorChannel.voltage
            # print('Raw ADC Value: ', self.sensorChannel.value)
        else:
            # just get the next value from the mock data
            voltage = self.mocked_data[self.mocked_data_idx]
            # update the index
            self.mocked_data_idx += 1
            if (self.mocked_data_idx >= len(self.mocked_data) + 1):
                self.mocked_data_idx = 0
        print('ADC Voltage: ' + str(voltage) + 'V')

        # calculate fuel level based on magnetic intensity
        distFromCenterVoltage = abs(voltage - 1)

        self.remainingLiters = self.voltsToLiters(distFromCenterVoltage)
        self.emaLiters = self.calcEMA(self.emaLiters, self.remainingLiters)
        self.remainingPerc = self.emaLiters / MAX_FUEL_CAPACITY

        print('Remaining percentage: ' + "{:.0f}".format(self.remainingPerc * 100) + '%')
        print('Remaining liters: ' +  "{:.2f}".format(self.remainingLiters))
        print('EMA liters: ' +  "{:.2f}".format(self.emaLiters))

    @staticmethod
    def voltsToLiters(voltage):
        """
        Returns the number of liters of fuel remaining based on the given
        normalized voltage.
        This uses an equation that was derived from manual tests.
        """
        return -0.176 + -0.648 * math.log(voltage)

    @staticmethod
    def calcEMA(curAvg, newVal):
        """
        Returns the exponential moving average given the current average and a new value.
        """
        return EMA_WEIGHT * newVal + (1 - EMA_WEIGHT) * curAvg
