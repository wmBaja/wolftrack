from functools import partial

from .ArduinoPoller import ArduinoPoller
from observerPattern.Subject import Subject
from .FuelPoller import FuelPoller

FUEL_DATA = 'fuel_data'
FUEL_POLLING_RATE = 2

GPS_DATA = 'gps_data'
GPS_POLLING_RATE = 0.2

ARDUINO_DATA = 'arduino_data'
ARDUINO_POLLING_RATE = 0

class HardwareManager(Subject):
  def __init__(self):
    super().__init__()
    self.pollerPool = [
      ArduinoPoller(ARDUINO_POLLING_RATE, partial(self.onData, ARDUINO_DATA))
    ]

  def onData(self, dataType, value):
    updates = []
    updates.append({'dataType': dataType, 'value': value})
    self.notify(updates)


  def startPollers(self):
    for poller in self.pollerPool:
      poller.start()

  def stopPollers(self):
    # tell each poller (thread) to stop
    for poller in self.pollerPool:
      poller.stopEvent.set()
