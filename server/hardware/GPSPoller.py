from .SensorPoller import SensorPoller

# import os to check if the machine is a RPI
import os
machineIsRaspberryPi = os.uname()[4].startswith('arm')

# if running on a RPI
if (machineIsRaspberryPi):
  # import libraries related to reading from the GPS module
  import busio
  import board
  import time
  import adafruit_gps

# the number of knots for every MPH
KNOTS_TO_MPH_CONV_FACTOR = 1.151

class GPSPoller(SensorPoller):
  """
  An independent thread that polls for a GPS data.
  """

  # the current latitude
  latitude = 0.0
  # the current longitude
  longitude = 0.0
  # the current speed
  speed = 0.0
  # the current track angle
  trackAngleDeg = 0.0

  def __init__(self, pollingRate, callback):
    newPollingRate = pollingRate / 2 - 0.005 # have to poll at least as twice as fast as the interval that you want data at
    super().__init__(newPollingRate, callback)
    # if running on a RPI
    if (machineIsRaspberryPi):
      # for a computer, use the pyserial library for uart access
      import serial
      uart = serial.Serial('/dev/ttyS0', baudrate=9600, timeout=3000)

      # Create a GPS module instance.
      self.gps = adafruit_gps.GPS(uart, debug=False)
      self.gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0') # set data that you want
      self.gps.send_command(bytes('PMTK220,' + str(pollingRate), 'utf-8')) # set polling rate
    else:
      # TODO find a way to mock data
      print('DO SET UP FOR MOCK DATA')

  def poll(self):
    """
    Retrieves GPS data from the GPS module.
    """
    # get the GPS data from the module
    self.getGPSData()
    return {
      'latitude': self.latitude,
      'longitude': self.longitude,
      'speed': self.speed,
      'trackAngle': self.trackAngleDeg
    }

  def getGPSData(self):
    """
    Gets the GPS data from the module.
    """
    # if running on a RPI
    if (machineIsRaspberryPi):
      # get the data from the GPS
      self.gps.update()
      if not self.gps.has_fix:
        # Try again if we don't have a fix yet.
        print('Waiting for fix...')
      else:
        # get the lat and lon
        self.latitude = self.gps.latitude
        self.longitude = self.gps.longitude
        if self.gps.speed_knots is not None:
          # get the speed in MPH
          self.speed = self.gps.speed_knots * KNOTS_TO_MPH_CONV_FACTOR
        if self.gps.track_angle_deg is not None:
          # get the tracking angle
          self.trackAngleDeg = self.gps.track_angle_deg

  def cleanup(self):
    """
    Abstract method; this should be defined by the child class
    """
    pass
