import dbus
try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject
from random import randint

from ..Characteristic import Characteristic
from ..dbusPaths import GATT_CHRC_IFACE

class HeartRateMeasurementChrc(Characteristic):
  HR_MSRMT_UUID = '00002a37-0000-1000-8000-00805f9b34fb'

  def __init__(self, bus, index, service):
    Characteristic.__init__(self, bus, index, self.HR_MSRMT_UUID, ['notify'], service)
    self.notifying = False
    self.hr_ee_count = 0

  def hr_msrmt_cb(self):
    value = []
    value.append(dbus.Byte(0x06))

    value.append(dbus.Byte(randint(90, 130)))

    if self.hr_ee_count % 10 == 0:
      value[0] = dbus.Byte(value[0] | 0x08)
      value.append(dbus.Byte(self.service.energy_expended & 0xff))
      value.append(dbus.Byte((self.service.energy_expended >> 8) & 0xff))

    self.service.energy_expended = \
            min(0xffff, self.service.energy_expended + 1)
    self.hr_ee_count += 1

    print('Updating value: ' + repr(value))

    self.PropertiesChanged(GATT_CHRC_IFACE, { 'Value': value }, [])

    return self.notifying

  def _update_hr_msrmt_simulation(self):
    print('Update HR Measurement Simulation')

    if not self.notifying:
      return

    GObject.timeout_add(1000, self.hr_msrmt_cb)

  def StartNotify(self):
    if self.notifying:
      print('Already notifying, nothing to do')
      return

    self.notifying = True
    self._update_hr_msrmt_simulation()

  def StopNotify(self):
    if not self.notifying:
      print('Not notifying, nothing to do')
      return

    self.notifying = False
    self._update_hr_msrmt_simulation()
