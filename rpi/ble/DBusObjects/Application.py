import dbus

# from .HeartRateService.HeartRateSrvc import HeartRateSrvc
# from .BatteryService.BatterySrvc import BatterySrvc
from .TestService.TestSrvc import TestSrvc
from .dbusPaths import DBUS_OM_IFACE

try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject

class Application(dbus.service.Object):
  """
  org.bluez.GattApplication1 interface implementation
  """
  def __init__(self, bus):
    self.path = '/'
    self.services = []
    dbus.service.Object.__init__(self, bus, self.path)

    self.dataSrvc = TestSrvc(bus, 0)
    self.add_service(self.dataSrvc)
    # self.add_service(HeartRateSrvc(bus, 1))
    # self.add_service(BatterySrvc(bus, 2))

  def updateTestChrc(self, value):
    self.dataSrvc.updateTestCharacteristic(value)
    return True

  def get_path(self):
    return dbus.ObjectPath(self.path)

  # add a new GATT service
  def add_service(self, service):
    self.services.append(service)

  @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
  def GetManagedObjects(self):
    response = {}

    for service in self.services:
      response[service.get_path()] = service.get_properties()
      chrcs = service.get_characteristics()
      for chrc in chrcs:
        response[chrc.get_path()] = chrc.get_properties()
        descs = chrc.get_descriptors()
        for desc in descs:
          response[desc.get_path()] = desc.get_properties()

    return response
