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

        speedLbl = QLabel('Speed (MPH)', self)
        grid.addWidget(speedLbl, 1, 0)

        self.speed = QLabel('0', self)
        grid.addWidget(self.speed, 1, 1)
        self.model.speedChange.connect(self.setSpeed)

        self.setGeometry(50, 50, 480, 320)
        self.setWindowTitle('WolfTrack')

    def setSpeed(self, speed):
        self.speed.setText(str(speed))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.model.quit()
