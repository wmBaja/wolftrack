from ..Service import Service
from .BatteryLevelChrc import BatteryLevelChrc

class BatterySrvc(Service):
  """
  Fake Battery service that emulates a draining battery.

  """
  BATTERY_UUID = '180f'

  def __init__(self, bus, index):
    Service.__init__(self, bus, index, self.BATTERY_UUID, True)
    self.add_characteristic(BatteryLevelChrc(bus, 0, self))

