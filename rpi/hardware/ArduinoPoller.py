from .SensorPoller import SensorPoller

import serial

class ArduinoPoller(SensorPoller):
  """
  An independent thread that polls for data from the Arduino.
  """

  # the current actuation
  actuation = 0

  def __init__(self, pollingRate, callback):
    """
    @param pollingRate - the polling rate in seconds
    """
    super().__init__(pollingRate, callback)
    self.serialConnection = serial.Serial('/dev/ttyACM0', 9600)

  def poll(self):
    """
    Retrieves data from the Arduino.
    """
    # get the data from the Arduino
    self.getArduinoData()
    return {
      'actuation': self.actuation,
    }

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
    byteArr = list((self.serialConnection.read(4)))
    intArr = self.getSensors(byteArr)
    self.actuation = intArr[0]

  def cleanup(self):
    """
    Abstract method; this should be defined by the child class
    """
    pass
