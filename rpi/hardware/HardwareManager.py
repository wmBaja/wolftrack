from functools import partial

from .ArduinoPoller import ArduinoPoller

FUEL_DATA = 'fuel_data'
FUEL_POLLING_RATE = 2

GPS_DATA = 'gps_data'
GPS_POLLING_RATE = 0.2

ARDUINO_DATA = 'arduino_data'
ARDUINO_POLLING_RATE = 0

class HardwareManager():
  def __init__(self, callback):
    super().__init__()
    self.onData = callback
    self.pollerPool = [
      ArduinoPoller(ARDUINO_POLLING_RATE, partial(self.onData, ARDUINO_DATA))
    ]

  def startPollers(self):
    for poller in self.pollerPool:
      poller.start()

  def stopPollers(self):
    # tell each poller (thread) to stop
    for poller in self.pollerPool:
      poller.stopEvent.set()
