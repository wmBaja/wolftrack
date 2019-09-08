from functools import partial

from .FuelPoller import FuelPoller

FUEL_DATA = 'fuel_data'
FUEL_POLLING_RATE = 1

class HardwareManager():
  def __init__(self, callback):
    super().__init__()
    self.onData = callback
    self.pollerPool = [
      FuelPoller(FUEL_POLLING_RATE, partial(self.onData, FUEL_DATA))
    ]

  def startPollers(self):
    for poller in self.pollerPool:
      poller.start()

  def stopPollers(self):
    # tell each poller (thread) to stop
    for poller in self.pollerPool:
      poller.stopEvent.set()
