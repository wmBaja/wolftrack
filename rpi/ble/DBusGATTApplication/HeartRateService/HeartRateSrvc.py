from ..Service import Service
from .HeartRateMeasurementChrc import HeartRateMeasurementChrc
from .BodySensorLocationChrc import BodySensorLocationChrc
from .HeartRateControlPointChrc import HeartRateControlPointChrc

class HeartRateSrvc(Service):
  """
  Fake Heart Rate Service that simulates a fake heart beat and control point
  behavior.

  """
  HR_UUID = '0000180d-0000-1000-8000-00805f9b34fb'

  def __init__(self, bus, index):
    Service.__init__(self, bus, index, self.HR_UUID, True)
    self.add_characteristic(HeartRateMeasurementChrc(bus, 0, self))
    self.add_characteristic(BodySensorLocationChrc(bus, 1, self))
    self.add_characteristic(HeartRateControlPointChrc(bus, 2, self))
    self.energy_expended = 0
