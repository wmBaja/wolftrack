#! /usr/bin/env python
"""
This is the main file for the Python application that runs on the RPi. It
serves as a go-between for the rest of the main components of the application.
It essentially follows an Observer design pattern which allows for the easy
introduction of further components which may be observers or subjects.
"""

import signal
import atexit

from blegatt.BLEGATTManager import BLEGATTManager
from hardware.HardwareManager import HardwareManager

# whether or not the program has been cleaned up yet
cleanedUp = False

# the BLE GATT manager
bleManager = None

# the hardware manager
hwManager = None

def cleanup():
  """
  Cleans up the program by:
    - Shutting down the BLE manager
    - Shutting down the hardware manager
  """
  global cleanedUp, hwManager, bleManager
  if not cleanedUp:
    print('Cleaning up')
    bleManager.stop()
    hwManager.stopPollers()
    cleanedUp = True

def sigintHandler(signal, frame):
  """
  A handler for kill signals that are captured.
  """
  cleanup()

def main():
  """
  Handles the instantiation and connection of the subjects and observers.
  Also handles setting up the capture of kill signals for clean shutdowns.
  """
  global hwManager, bleManager
  # catch the kill signal to end gracefully
  signal.signal(signal.SIGINT, sigintHandler)
  # cleanup when exiting
  atexit.register(cleanup)

  bleManager = BLEGATTManager()
  hwManager = HardwareManager()

  # connect BLEGATTManager to HardwareManager
  hwManager.attach(bleManager)

  bleManager.start() # start the BLE GATT server
  hwManager.startPollers() # start the sensor pollers


if __name__ == '__main__':
  main()
