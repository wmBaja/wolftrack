from ..Characteristic import Characteristic
from ..errors import InvalidValueLengthException, FailedException

class HeartRateControlPointChrc(Characteristic):
  HR_CTRL_PT_UUID = '00002a39-0000-1000-8000-00805f9b34fb'

  def __init__(self, bus, index, service):
    Characteristic.__init__(
            self, bus, index,
            self.HR_CTRL_PT_UUID,
            ['write'],
            service)

  def WriteValue(self, value, options):
    print('Heart Rate Control Point WriteValue called')

    if len(value) != 1:
      raise InvalidValueLengthException()

    byte = value[0]
    print('Control Point value: ' + repr(byte))

    if byte != 1:
      raise FailedException("0x80")

    print('Energy Expended field reset!')
    self.service.energy_expended = 0
