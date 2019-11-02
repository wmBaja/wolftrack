import dbus

from .errors import InvalidArgsException
from .dbusPaths import GATT_SERVICE_IFACE, DBUS_PROP_IFACE

class Service(dbus.service.Object):
  """
  org.bluez.GattService1 interface implementation
  """
  PATH_BASE = '/org/bluez/example/service'

  def __init__(self, bus, index, uuid, primary):
    self.path = self.PATH_BASE + str(index)
    self.bus = bus
    self.uuid = uuid
    self.primary = primary
    self.characteristics = []
    dbus.service.Object.__init__(self, bus, self.path)

  def get_properties(self):
    return {
      GATT_SERVICE_IFACE: {
        'UUID': self.uuid,
        'Primary': self.primary,
        'Characteristics': dbus.Array(
                self.get_characteristic_paths(),
                signature='o')
      }
    }

  def get_path(self):
    return dbus.ObjectPath(self.path)

  def add_characteristic(self, characteristic):
    self.characteristics.append(characteristic)

  def get_characteristic_paths(self):
    result = []
    for chrc in self.characteristics:
      result.append(chrc.get_path())
    return result

  def get_characteristics(self):
    return self.characteristics

  @dbus.service.method(DBUS_PROP_IFACE,
                        in_signature='s',
                        out_signature='a{sv}')
  def GetAll(self, interface):
    if interface != GATT_SERVICE_IFACE:
      raise InvalidArgsException()

    return self.get_properties()[GATT_SERVICE_IFACE]