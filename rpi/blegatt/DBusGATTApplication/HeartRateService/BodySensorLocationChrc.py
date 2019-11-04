from ..Characteristic import Characteristic

class BodySensorLocationChrc(Characteristic):
  BODY_SNSR_LOC_UUID = '00002a38-0000-1000-8000-00805f9b34fb'

  def __init__(self, bus, index, service):
    Characteristic.__init__(
            self, bus, index,
            self.BODY_SNSR_LOC_UUID,
            ['read'],
            service)

  def ReadValue(self, options):
    # Return 'Chest' as the sensor location.
    return [ 0x01 ]