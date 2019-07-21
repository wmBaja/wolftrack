#!/usr/bin/python3

from PyQt5.QtCore import QThread, QTimer, QEventLoop

class SensorPoller(QThread):
    def __init__(self, pollingRate):
        super().__init__()
        self.pollingRate = pollingRate
        # init the timer and move it to this thread
        self.timer = QTimer()
        self.timer.moveToThread(self)

    # run method gets called when we start the thread
    def run(self):
        # connect the poll method to the timer's timeout signal
        self.timer.timeout.connect(self.poll)
        # start the timer and make it trigger its signal at the polling rate
        self.timer.start(self.pollingRate)
        # start an event loop to keep this thread alive
        loop = QEventLoop()
        loop.exec_()

    # abstract method; should be defined by a child class
    def poll(self):
        pass
