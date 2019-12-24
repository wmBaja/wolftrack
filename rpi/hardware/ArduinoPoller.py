from .SensorPoller import SensorPoller

import serial

from random import randrange
import time

# the baud rate for the serial connection to the Arduino
BAUD_RATE = 115200

class ArduinoPoller(SensorPoller):
  """
  An independent thread that polls for data from the Arduino.
  """

  def __init__(self, pollingRate, callback):
    """
    @param pollingRate - the polling rate in seconds
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
    return int.from_bytes(arr, byteorder='big', signed=False)

  def getArduinoData(self):
    """
    Gets the data from the Arduino.
    """
    if (self.serialConnection):
      byteArr = list((self.serialConnection.read(4)))
      # intArr = self.getSensors(byteArr)
      # return intArr[0]
      return byteArr
    else:
      time.sleep(1)
      return self.generateRandomByteList(8)

  def generateRandomByteList(self, num16BitUints):
    arr = []
    for x in range(0, num16BitUints):
      arr.append(randrange(4))
      arr.append(randrange(256))
    return arr

  def cleanup(self):
    """
    Abstract method; this should be defined by the child class
    """
    pass
