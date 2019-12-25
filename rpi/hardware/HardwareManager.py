from functools import partial

from .ArduinoPoller import ArduinoPoller
from observerPattern.Subject import Subject

# The data type for data from the ArduinoPoller
ARDUINO_DATA = 'arduino_data'
# The polling rate for the ArduinoPoller
ARDUINO_POLLING_RATE = 0 # (no polling rate; i.e. there should be a blocking call in the poller)

class HardwareManager(Subject):
  """
  Manages all interactions with hardware (sensors, pins, etc).
  """
  def __init__(self):
    """
    Populates the poller pool.
    """
    super().__init__()
    self.pollerPool = [
      ArduinoPoller(ARDUINO_POLLING_RATE, partial(self.onData, ARDUINO_DATA))
    ]

  def onData(self, dataType, value):
    """
    A callback for pollers when they have new data.
    """
    updates = []
    updates.append({'dataType': dataType, 'value': value})
    self.notify(updates)

  def startPollers(self):
    """
    Starts each poller.
    """
    for poller in self.pollerPool:
      poller.start()

  def stopPollers(self):
    """
    Tells each poller to stop.
    """
    for poller in self.pollerPool:
      poller.stop()
