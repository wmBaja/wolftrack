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

# the range of voltages that do not warrant any significant magnetic field
# detection by the hall sensor on the fuel tank
NO_MAG_FIELD_VOLTAGE_RANGE = [0.97, 1.03]

# the lowest voltage value given by the hall sensor
LOWEST_VOLTAGE = 0.05

# the highest voltage value given by the hall sensor
HIGHEST_VOLTAGE = 2.01

# the difference between the lowest voltage value and the low end of the
# no-mag-field voltage range
DIF_LOWEST_VOLTAGE_NMF_RANGE = NO_MAG_FIELD_VOLTAGE_RANGE[0] - LOWEST_VOLTAGE

# the difference between the highest voltage value and the high end of the
# no-mag-field voltage range
DIF_HIGHEST_VOLTAGE_NMF_RANGE = HIGHEST_VOLTAGE - NO_MAG_FIELD_VOLTAGE_RANGE[1]

# the percentage (as a value between 0.0 and 1.0) of fuel remaining when the
# hall sensor first detects a magnetic field
INITIAL_PERC_FUEL = 0.5 # the hall sensor can detect the magnet when there is
                        # approximately half a tank of fuel remaining

class FuelPoller(SensorPoller):
    """
    This object serves as an independent thread that polls for a fuel level.
    """
    # signal that emits the current fuel level as a float (between 0.0 and 1.0)
    signal = pyqtSignal(float)
    # the percentage (as a value between 0.0 and 1.0) of fuel remaining
    remainingFuel = 0.6

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

    def poll(self):
        # calculate the remaining fuel
        self.calculateRemainingFuel()
        # emit fuel percentage value
        self.signal.emit(self.remainingFuel)

    def calculateRemainingFuel(self):
        voltage = 1
        # if running on a RPI
        if (machineIsRaspberryPi):
            voltage = self.sensorChannel.voltage
            # print('Raw ADC Value: ', self.sensorChannel.value)
            # print('ADC Voltage: ' + str(voltage) + 'V')
        else:
            # just generate a random voltage value
            voltage = random.random() * (HIGHEST_VOLTAGE - LOWEST_VOLTAGE) + 0.05
            print('ADC Voltage: ' + str(voltage) + 'V')

        # calculate fuel level based on magnetic intensity
        # if the voltage is within the no-mag-field range
        if (voltage >= NO_MAG_FIELD_VOLTAGE_RANGE[0] and voltage <= NO_MAG_FIELD_VOLTAGE_RANGE[1]):
            # the fuel level is guaranteed to be at least at the initial
            # level at which the magnet can be detected
            self.remainingFuel = INITIAL_PERC_FUEL
        # else if the voltage is below the no-mag-field range
        elif (voltage < NO_MAG_FIELD_VOLTAGE_RANGE[0]):
            fuelUsed = (NO_MAG_FIELD_VOLTAGE_RANGE[0] - voltage) / (DIF_LOWEST_VOLTAGE_NMF_RANGE) * INITIAL_PERC_FUEL
            self.remainingFuel = INITIAL_PERC_FUEL - fuelUsed
        # else if the voltage is above the no-mag-field range
        elif (voltage > NO_MAG_FIELD_VOLTAGE_RANGE[1]):
            fuelUsed = (voltage - NO_MAG_FIELD_VOLTAGE_RANGE[1]) / (DIF_HIGHEST_VOLTAGE_NMF_RANGE) * INITIAL_PERC_FUEL
            self.remainingFuel = INITIAL_PERC_FUEL - fuelUsed

        print('Remaining fuel: ' + str(self.remainingFuel))
