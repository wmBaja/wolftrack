#!/usr/bin/python3

from PyQt5.QtWidgets import QWidget, QGridLayout, QLCDNumber, QLabel
from PyQt5.QtGui import QPainter, QFont
from PyQt5.QtCore import Qt, QTime, QTimer
import sys, random

from DigitalClock import DigitalClock

class MainWindow(QWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model

        self.setFont(QFont('SansSerif', 20))

        grid = QGridLayout()
        self.setLayout(grid)

        title = QLabel('Current Time', self)
        grid.addWidget(title, 0, 0)

        self.clock = DigitalClock(self)
        grid.addWidget(self.clock, 0, 1)

        # speed
        speedLbl = QLabel('Speed (MPH)', self)
        grid.addWidget(speedLbl, 1, 0)

        self.speed = QLCDNumber(self)
        self.speed.setSegmentStyle(QLCDNumber.Filled)
        self.speed.setDigitCount(3)
        grid.addWidget(self.speed, 1, 1)
        self.model.speedChange.connect(self.setSpeed)

        # fuel percentage
        fuelPercLbl = QLabel('Fuel (%)', self)
        grid.addWidget(fuelPercLbl, 2, 0)

        self.fuelPerc = QLCDNumber(self)
        self.fuelPerc.setSegmentStyle(QLCDNumber.Filled)
        self.fuelPerc.setDigitCount(3)
        grid.addWidget(self.fuelPerc, 2, 1)

        # fuel liters
        fuelLitersLbl = QLabel('Fuel (L)', self)
        grid.addWidget(fuelLitersLbl, 3, 0)

        self.fuelLiters = QLCDNumber(self)
        self.fuelLiters.setSegmentStyle(QLCDNumber.Filled)
        self.fuelLiters.setDigitCount(4)
        grid.addWidget(self.fuelLiters, 3, 1)

        self.model.fuelChange.connect(self.setFuel)

        self.setGeometry(50, 50, 480, 320)
        self.setWindowTitle('WolfTrack')

    def setSpeed(self, speed):
        self.speed.display(str(speed))

    def setFuel(self, fuelPerc, fuelLiters):
        self.fuelPerc.display("{:.0f}".format(fuelPerc * 100))
        self.fuelLiters.display("{:.2f}".format(fuelLiters))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.model.quit()
