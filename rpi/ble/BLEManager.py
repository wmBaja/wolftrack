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
from .DBusObjects.Application import Application
from .DBusObjects.dbusPaths import BLUEZ_SERVICE_NAME, DBUS_OM_IFACE, DBUS_PROP_IFACE, GATT_MANAGER_IFACE, BLUETOOTH_ADAPTER_IFACE, LE_ADVERTISING_MANAGER_IFACE

from .DBusObjects.TestAdvertisement import TestAdvertisement



class BLEManager(Observer, Thread):
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

  def register_ad_cb(self):
    print('Advertisement registered')

  def register_ad_error_cb(self, error):
    print('Failed to register advertisement: ' + str(error))
    self.mainloop.quit()

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

  def find_bluetooth_adapter(self, bus):
    """
    Finds the Bluetooth adapter on the given bus.
    """
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                                DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()

    for o, props in objects.items():
      if BLUETOOTH_ADAPTER_IFACE in props.keys():
        return o

    return None

  def run(self):
    """
    Setup BLE advertising and the GATT server.
    """
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    self.mainloop = GObject.MainLoop()

    bus = dbus.SystemBus()

    bluetooth_adapter = self.find_bluetooth_adapter(bus)#GATT_MANAGER_IFACE)
    if not bluetooth_adapter:
      print('Bluetooth adapter interface not found')
      return

    adapter_props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, bluetooth_adapter),
                                   DBUS_PROP_IFACE)

    # ensure that the Bluetooth adapter is powered on
    adapter_props.Set(BLUETOOTH_ADAPTER_IFACE, 'Powered', dbus.Boolean(1))

    # get LE advertising manager
    ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, bluetooth_adapter),
                                LE_ADVERTISING_MANAGER_IFACE)
    print(ad_manager)

    self.advertisement = TestAdvertisement(bus, 0)

    print('Registering LE advertisement...')
    ad_manager.RegisterAdvertisement(self.advertisement.get_path(), {},
                                     reply_handler=self.register_ad_cb,
                                     error_handler=self.register_ad_error_cb)

    # get GATT manager
    gatt_manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, bluetooth_adapter),
            GATT_MANAGER_IFACE)

    self.app = Application(bus)

    print('Registering GATT application...')
    gatt_manager.RegisterApplication(self.app.get_path(), {},
                                    reply_handler=self.register_app_cb,
                                    error_handler=self.register_app_error_cb)

    # start main loop
    self.mainloop.run() # blocks until self.mainloop.quit() is called

    # unregister LE advertisement
    ad_manager.UnregisterAdvertisement(self.advertisement)
    print('LE Advertisement unregistered.')
    dbus.service.Object.remove_from_connection(self.advertisement)

    # unregister GATT app
    gatt_manager.UnregisterApplication(self.app)
    print('GATT application unregistered.')
    dbus.service.Object.remove_from_connection(self.app)


  def stop(self):
    self.mainloop.quit()
