from threading import Thread, Event
import dbus
import dbus.mainloop.glib

import array
try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject
import sys

from random import randint


from observerPattern.Observer import Observer
from .DBusGATTApplication.Application import Application
from .DBusGATTApplication.dbusPaths import BLUEZ_SERVICE_NAME, DBUS_OM_IFACE, GATT_MANAGER_IFACE




class BLEGATTManager(Observer, Thread):
  def __init__(self):
    super().__init__()
    self.mainloop = None
    self.app = None

  def update(self, updates):
    """
    The update method for an Observer in the observer pattern.
    This is what updates the characteristic in the BLE GATT server.
    """
    for update in updates:
      if self.app and update['dataType'] == 'arduino_data':
        print('Received Arduino data in BLEGATTManager')
        print('{}: {}'.format(update['dataType'], str(update['value'])))
        self.app.updateTestChrc(update['value'])

  def register_app_cb(self):
    """
    Called when the GATT application is successfully registered through dbus.
    """
    print('GATT application registered')

  def register_app_error_cb(self, error):
    """
    Called when the GATT application fails to be registered.
    """
    print('Failed to register application: ' + str(error))
    self.mainloop.quit()

  def find_adapter(self, bus):
    """
    Finds the adapter with the given interface on the given bus.
    """
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                                DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()

    for o, props in objects.items():
      if GATT_MANAGER_IFACE in props.keys():
        return o

    return None

  def run(self):
    """
    Setup BLE advertising and the GATT server.
    """

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()

    adapter = self.find_adapter(bus)
    if not adapter:
      print('GattManager1 interface not found')
      return

    service_manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, adapter),
            GATT_MANAGER_IFACE)

    self.app = Application(bus)

    self.mainloop = GObject.MainLoop()

    print('Registering GATT application...')

    service_manager.RegisterApplication(self.app.get_path(), {},
                                    reply_handler=self.register_app_cb,
                                    error_handler=self.register_app_error_cb)

    self.mainloop.run()

