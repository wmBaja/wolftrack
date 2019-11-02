import dbus
try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject

from ..Characteristic import Characteristic
from ..dbusPaths import GATT_CHRC_IFACE

class BatteryLevelChrc(Characteristic):
  """
  Fake Battery Level characteristic. The battery level is drained by 2 points
  every 5 seconds.
  """
  BATTERY_LVL_UUID = '2a19'

  def __init__(self, bus, index, service):
    Characteristic.__init__(
            self, bus, index,
            self.BATTERY_LVL_UUID,
            ['read', 'notify'],
            service)
    self.notifying = False
    self.battery_lvl = 100
    GObject.timeout_add(5000, self.drain_battery)

  def notify_battery_level(self):
    if not self.notifying:
      return
    self.PropertiesChanged(
            GATT_CHRC_IFACE,
            { 'Value': [dbus.Byte(self.battery_lvl)] }, [])

  def drain_battery(self):
    if not self.notifying:
      return True
    if self.battery_lvl > 0:
      self.battery_lvl -= 2
      if self.battery_lvl < 0:
        self.battery_lvl = 0
    print('Battery Level drained: ' + repr(self.battery_lvl))
    self.notify_battery_level()
    return True

  def ReadValue(self, options):
    print('Battery Level read: ' + repr(self.battery_lvl))
    return [dbus.Byte(self.battery_lvl)]

  def StartNotify(self):
    if self.notifying:
      print('Already notifying, nothing to do')
      return

    self.notifying = True
    self.notify_battery_level()

  def StopNotify(self):
    if not self.notifying:
      print('Not notifying, nothing to do')
      return

    self.notifying = False
