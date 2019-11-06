import dbus.service

from .errors import InvalidArgsException, NotSupportedException
from .dbusPaths import GATT_DESC_IFACE, DBUS_PROP_IFACE

class Descriptor(dbus.service.Object):
  """
  org.bluez.GattDescriptor1 interface implementation
  """
  def __init__(self, bus, index, uuid, flags, characteristic):
    self.path = characteristic.path + '/desc' + str(index)
    self.bus = bus
    self.uuid = uuid
    self.flags = flags
    self.chrc = characteristic
    dbus.service.Object.__init__(self, bus, self.path)

  def get_properties(self):
    return {
      GATT_DESC_IFACE: {
        'Characteristic': self.chrc.get_path(),
        'UUID': self.uuid,
        'Flags': self.flags,
      }
    }

  def get_path(self):
    return dbus.ObjectPath(self.path)

  @dbus.service.method(DBUS_PROP_IFACE,
                        in_signature='s',
                        out_signature='a{sv}')
  def GetAll(self, interface):
    if interface != GATT_DESC_IFACE:
      raise InvalidArgsException()

    return self.get_properties()[GATT_DESC_IFACE]

  @dbus.service.method(GATT_DESC_IFACE,
                      in_signature='a{sv}',
                      out_signature='ay')
  def ReadValue(self, options):
    print ('Default ReadValue called, returning error')
    raise NotSupportedException()

  @dbus.service.method(GATT_DESC_IFACE, in_signature='aya{sv}')
  def WriteValue(self, value, options):
    print('Default WriteValue called, returning error')
    raise NotSupportedException()
