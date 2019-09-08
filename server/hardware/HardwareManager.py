from functools import partial

from .FuelPoller import FuelPoller
from .GPSPoller import GPSPoller

FUEL_DATA = 'fuel_data'
FUEL_POLLING_RATE = 1

GPS_DATA = 'gps_data'
GPS_POLLING_RATE = 0.5

class HardwareManager():
  def __init__(self, callback):
    super().__init__()
    self.onData = callback
    self.pollerPool = [
      FuelPoller(FUEL_POLLING_RATE, partial(self.onData, FUEL_DATA)),
      GPSPoller(GPS_POLLING_RATE, partial(self.onData, GPS_DATA))
    ]

  def startPollers(self):
    for poller in self.pollerPool:
      poller.start()

  def stopPollers(self):
    # tell each poller (thread) to stop
    for poller in self.pollerPool:
      poller.stopEvent.set()
