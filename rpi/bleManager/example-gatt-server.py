#!/usr/bin/env python3

import dbus

import array
try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject
import sys

from random import randint


from .DBusGATTApplication.Application import Application
from .DBusGATTApplication.dbusPaths import BLUEZ_SERVICE_NAME, DBUS_OM_IFACE, GATT_MANAGER_IFACE


mainloop = None


def register_app_cb():
  print('GATT application registered')


def register_app_error_cb(error):
  print('Failed to register application: ' + str(error))
  mainloop.quit()


def find_adapter(bus):
  remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                              DBUS_OM_IFACE)
  objects = remote_om.GetManagedObjects()

  for o, props in objects.items():
    if GATT_MANAGER_IFACE in props.keys():
      return o

  return None

def main():
  global mainloop

  dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

  bus = dbus.SystemBus()

  adapter = find_adapter(bus)
  if not adapter:
    print('GattManager1 interface not found')
    return

  service_manager = dbus.Interface(
          bus.get_object(BLUEZ_SERVICE_NAME, adapter),
          GATT_MANAGER_IFACE)

  app = Application(bus)

  mainloop = GObject.MainLoop()

  print('Registering GATT application...')

  service_manager.RegisterApplication(app.get_path(), {},
                                  reply_handler=register_app_cb,
                                  error_handler=register_app_error_cb)

  mainloop.run()

if __name__ == '__main__':
  main()

