#!/usr/bin/python3

from PyQt5.QtCore import QTime, QTimer
from PyQt5.QtWidgets import QLCDNumber

class DigitalClock(QLCDNumber):
    def __init__(self, parent):
        super().__init__(parent)

        self.setSegmentStyle(QLCDNumber.Filled)
        self.setDigitCount(8)

        timer = QTimer(self)
        timer.timeout.connect(self.showTime)
        timer.start(1000)

        self.showTime()

    def showTime(self):
        time = QTime.currentTime()
        text = time.toString('hh:mm:ss')

        self.display(text)
