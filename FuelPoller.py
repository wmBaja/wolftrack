#!/usr/bin/python3

from PyQt5.QtCore import pyqtSignal
from SensorPoller import SensorPoller

isRPI = True
if (isRPI):
    import busio
    import digitalio
    import board
    import adafruit_mcp3xxx.mcp3008 as MCP
    from adafruit_mcp3xxx.analog_in import AnalogIn

class FuelPoller(SensorPoller):
    signal = pyqtSignal(float)
    fuel = 1.0

    def __init__(self, pollingRate):
        super().__init__(pollingRate)
        if (isRPI):
            # create the spi bus
            spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)

            # create the cs (chip select)
            cs = digitalio.DigitalInOut(board.D5)

            # create the mcp object
            mcp = MCP.MCP3008(spi, cs)

            # create an analog input channel on pin 0
            self.chan0 = AnalogIn(mcp, MCP.P0)

    def poll(self):
        # TODO read from hall sensor on fuel tank
        # TODO calculate fuel level based on magnetic intensity
        self.fuel = self.fuel - 0.05
        if (self.fuel < 0):
            self.fuel = 1.0

        if (isRPI):
            print('Raw ADC Value: ', self.chan0.value)
            print('ADC Voltage: ' + str(self.chan0.voltage) + 'V')

        # emit with value
        self.signal.emit(self.fuel)
