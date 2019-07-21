#!/usr/bin/python3

from PyQt5.QtCore import QThread, QTimer, pyqtSignal, QEventLoop
import random
from SensorPoller import SensorPoller

class SpeedPoller(SensorPoller):
    signal = pyqtSignal(int)
    speed = 0

    def __init__(self, pollingRate):
        super().__init__(pollingRate)

    def poll(self):
        # TODO read from hall sensor on wheel
        # TODO calculate speed based on RPM of wheel
        # this will probably need to be implemented differently since the
        # data you actually want requires at least two readings from the hall
        # sensor (on or off) along with the times in between those readings
        self.speed = self.speed + 1
        if (self.speed > 100):
            self.speed = 0

        # emit with value
        self.signal.emit(self.speed)
