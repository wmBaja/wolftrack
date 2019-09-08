from .SensorPoller import SensorPoller

import random

class FuelPoller(SensorPoller):
  """
  An independent thread that polls for a fuel level.
  """
  def __init__(self, pollingRate, callback):
    super().__init__(pollingRate, callback)

  def poll(self):
    """
    Calculates the current fuel level based on the voltage read from the
    Hall-effect sensor.
    """
    return random.random()
    # pass

  def cleanup(self):
    """
    Abstract method; this should be defined by the child class
    """
    pass
