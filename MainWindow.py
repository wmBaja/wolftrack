#!/usr/bin/python3

from PyQt5.QtWidgets import QWidget, QGridLayout, QLCDNumber, QLabel
from PyQt5.QtGui import QPainter, QFont, QColor, QPen
from PyQt5.QtCore import Qt, QTime, QTimer, QThread, QEventLoop, pyqtSignal
import sys, random

from FuelPoller import MAX_FUEL_CAPACITY, MAX_DETECTED_FUEL_CAPACITY
MAX_DETECTED_FUEL_PERCENTAGE = MAX_DETECTED_FUEL_CAPACITY / MAX_FUEL_CAPACITY

# this is the percentage at which the fuel level is critical and the user should be alerted
FUEL_PERCENTAGE_ALERT_POINT = 0.2

# the time that it takes for the number to appear and disappear
ALERT_FLASH_INTERVAL = 500

from DigitalClock import DigitalClock

class AlertThread(QThread):
    """
    This class serves as a thread that simply toggles the LCD numbers on or off.
    """
    # signal that emits an integer
    signal = pyqtSignal(bool)

    switchedOn = False
    def __init__(self):
        super().__init__()
        # init the timer and move it to this thread
        self.timer = QTimer()
        self.timer.moveToThread(self)

    # run method gets called when we start the thread
    def run(self):
        # connect the handle method to the timer's timeout signal
        self.timer.timeout.connect(self.handle)
        # start the timer and make it switch its signal at the alert flash interval
        self.timer.start(ALERT_FLASH_INTERVAL)
        # start an event loop to keep this thread alive
        loop = QEventLoop()
        loop.exec_()

    # abstract method; should be defined by a child class
    def handle(self):
        self.signal.emit(self.switchedOn)
        self.switchedOn = not self.switchedOn

class MainWindow(QWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model

        # lcd number
        self.alertThread = AlertThread()
        self.alertThread.signal.connect(self.switchLCDDisplay)
        self.alertThread.start()

        self.setFont(QFont('Monospace', 20))

        grid = QGridLayout()
        self.setLayout(grid)

        # title = QLabel('Current Time', self)
        # grid.addWidget(title, 0, 0)

        # self.clock = DigitalClock(self)
        # grid.addWidget(self.clock, 0, 1)

        # speed
        # speedLbl = QLabel('Speed (MPH)', self)
        # grid.addWidget(speedLbl, 1, 0)

        # self.speed = QLCDNumber(self)
        # self.speed.setSegmentStyle(QLCDNumber.Filled)
        # self.speed.setDigitCount(3)
        # grid.addWidget(self.speed, 1, 1)
        # self.model.speedChange.connect(self.setSpeed)

        # fuel percentage
        # fuelPercLbl = QLabel('Fuel (%)', self)
        # grid.addWidget(fuelPercLbl, 1, 0)

        self.fuelPercLCD = QLCDNumber(self)
        self.fuelPercLCD.setSegmentStyle(QLCDNumber.Filled)
        self.fuelPercLCD.setDigitCount(2)
        grid.addWidget(self.fuelPercLCD, 0, 0)

        # fuel liters
        # fuelLitersLbl = QLabel('Fuel (L)', self)
        # grid.addWidget(fuelLitersLbl, 2, 0)

        # self.fuelLiters = QLCDNumber(self)
        # self.fuelLiters.setSegmentStyle(QLCDNumber.Filled)
        # self.fuelLiters.setDigitCount(4)
        # grid.addWidget(self.fuelLiters, 2, 1)

        self.model.fuelChange.connect(self.setFuel)

        self.setGeometry(50, 50, 480, 320)
        self.setWindowTitle('WolfTrack')

    def switchLCDDisplay(self, switchedOn):
        if (self.fuelPerc <= FUEL_PERCENTAGE_ALERT_POINT):
            if (switchedOn):
                self.fuelPercLCD.show()
            else:
                self.fuelPercLCD.hide()
        else:
            self.fuelPercLCD.show()

    def setFuel(self, fuelPerc, fuelLiters):
        self.fuelPerc = fuelPerc
        percent = fuelPerc * 100
        percentString = "{:.0f}".format(percent)
        self.fuelPercLCD.display(percentString)
        self.repaint()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.model.quit()

    def paintEvent(self, e):

        qp = QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()


    def drawWidget(self, qp):
        size = self.size()
        w = size.width()
        h = size.height()

        normalizedFuelPerc = (self.fuelPerc - FUEL_PERCENTAGE_ALERT_POINT) / (MAX_DETECTED_FUEL_PERCENTAGE - FUEL_PERCENTAGE_ALERT_POINT)
        if (normalizedFuelPerc < 0.0):
            normalizedFuelPerc = 0
        color = MainWindow.mapFuelPercentageToColor(normalizedFuelPerc)

        qp.setPen(QColor(color['r'], color['g'], color['b']))
        qp.setBrush(QColor(color['r'], color['g'], color['b']))
        # qp.setBrush(QColor(240, 15, 0))
        # qp.drawRect(0, h, w, -till)
        qp.drawRect(0, 0, w, h / 14) # top rectangle
        qp.drawRect(0, h / 14, w / 5, h - h / 7) # left rectangle
        qp.drawRect(w - w / 5, h / 14, w / 5, h - h / 7) # right rectangle
        qp.drawRect(0, h - h / 14, w, h / 14)


        pen = QPen(QColor(20, 20, 20), 1, Qt.SolidLine)

        # draw outer box
        qp.setPen(pen)
        qp.setBrush(Qt.NoBrush)
        qp.drawRect(0, 0, w-1, h-1)

    @staticmethod
    def mapFuelPercentageToColor(curPerc):
        """
        Returns the color that corresponds to the given fuel percentage.
        The fuel percentage should be given as a decimal (0.0 - 1.0).
        """
        RED_START_VAL = 0
        GREEN_START_VAL = 255
        BLUE_START_VAL = 0
        RED_END_VAL = 255
        GREEN_END_VAL = 0
        BLUE_END_VAL = 0

        red = curPerc * RED_START_VAL + (1 - curPerc) * RED_END_VAL
        green = curPerc * GREEN_START_VAL + (1 - curPerc) * GREEN_END_VAL
        blue = curPerc * BLUE_START_VAL + (1 - curPerc) * BLUE_END_VAL
        return {'r': red, 'g': green, 'b': blue}
