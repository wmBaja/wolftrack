#!/usr/bin/python3

from PyQt5.QtCore import pyqtSignal
from SensorPoller import SensorPoller

class FuelPoller(SensorPoller):
    signal = pyqtSignal(float)
    fuel = 1.0

    def __init__(self, pollingRate):
        super().__init__(pollingRate)

    def poll(self):
        # TODO read from hall sensor on fuel tank
        # TODO calculate fuel level based on magnetic intensity
        self.fuel = self.fuel - 0.05
        if (self.fuel < 0):
            self.fuel = 1.0

        # emit with value
        self.signal.emit(self.fuel)
