#! /usr/bin/env python
"""
This is the main file for the Python application that runs on the RPi. It
serves as a go-between for the rest of the main components of the application.
It essentially follows an Observer design pattern which allows for the easy
introduction of further components which may be observers or subjects.
"""

import signal
import atexit

# the hardware manager is a subject
from hardware.HardwareManager import HardwareManager

# whether or not the program has been cleaned up yet
cleanedUp = False

# the hardware manager
hwManager = None

def cleanup():
  """
  Cleans up the program by:
    - Shutting down the hardware manager
  """
  global cleanedUp, hwManager
  if not cleanedUp:
    print('Cleaning up')
    hwManager.stopPollers()
    cleanedUp = True

def sigintHandler(signal, frame):
  """
  A handler for kill signals that are captured.
  """
  cleanup()
  quit()

def onHwData(dataType, value):
  """
  A callback for getting hardware data.
  """
  print(str(dataType) + ': ' + str(value))

def main():
  """
  Handles the instantiation and connection of the subjects and observers.
  Also handles setting up the capture of kill signals for clean shutdowns.
  """
  global hwManager
  # catch the kill signal to end gracefully
  signal.signal(signal.SIGINT, sigintHandler)
  # cleanup when exiting
  atexit.register(cleanup)

  # TODO connect observers to subjects
  # Connections to make:
  #   - BLEGATTManager -> HardwareManager
  #   - DBManager      -> HardwareManager
  #   - BLEGATTManager -> ?? (for commands from the device connected over BLE)

  hwManager = HardwareManager(onHwData)
  hwManager.startPollers() # start the sensor pollers

  # TODO need some way of keeping the main app alive (probably some sort of loop like GLib's)


if __name__ == '__main__':
  main()
