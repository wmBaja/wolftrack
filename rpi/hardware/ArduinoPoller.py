from .SensorPoller import SensorPoller

import serial

from random import randrange
import time

# The baud rate for the serial connection to the Arduino
BAUD_RATE = 115200
# the interval on which random data will be generated
RANDOM_DATA_GENERATION_INTERVAL = 0.1

class ArduinoPoller(SensorPoller):
  """
  An independent thread that polls for data from the Arduino.
  """
  def __init__(self, pollingRate, callback):
    """
    Attempts to establish a serial connection with the Arduino.
    @param pollingRate - the polling rate in seconds (should be 0)
    @param callback - a function that will be called whenever new data is polled
    """
    super().__init__(pollingRate, callback)
    self.serialConnection = None
    try:
      self.serialConnection = serial.Serial('/dev/ttyACM0', BAUD_RATE)
    except:
      print('Could not connect to Arduino through serial connection.  Generating random numbers.')

  def poll(self):
    """
    Retrieves data from the Arduino and returns it so that it can be used by SensorPoller.
    """
    # get the data from the Arduino
    data = self.getArduinoData()
    return data

  def getSensors(self, sen):
    """
    Returns a list of 16-bit unsigned integers derived from the passed in byte list.
    """
    alength = len(sen)
    a = []
    for x in range(0, alength, 2):
      if x == 0:
        b = sen[0:2]
        a.append(self.getValue(b))
      else:
        b = sen[x*2:x*2+2]
        a.append(self.getValue(b))
    return a

  def getValue(self, arr):
    """
    Returns an integer value from an array of bytes.
    """
    return int.from_bytes(arr, byteorder='big', signed=False)

  def getArduinoData(self):
    """
    Reads and returns data from the Arduino.
    """
    if (self.serialConnection):
      byteArr = list((self.serialConnection.read(16)))
      # intArr = self.getSensors(byteArr)
      # return intArr[0]
      return byteArr
    else:
      time.sleep(RANDOM_DATA_GENERATION_INTERVAL)
      data = self.generateRandomByteList(8)
      # print(data)
      return data

  def generateRandomByteList(self, num16BitUints):
    """
    Returns a list of random bytes based on the number of 16-bit unsigned
    integers that should be represented by the list.
    @param num16BitUints - the number of 16-bit unsigned integers that
      should be represented by the list
    """
    arr = []
    for x in range(0, num16BitUints):
      arr.append(randrange(4))
      arr.append(randrange(256))
    return arr

  def cleanup(self):
    """
    Closes the serial connection.
    Called by SensorPoller.
    """
    if (self.serialConnection):
      self.serialConnection.close()
