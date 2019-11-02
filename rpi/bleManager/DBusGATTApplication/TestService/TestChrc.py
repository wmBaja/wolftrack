from ..Characteristic import Characteristic
from .TestDscr import TestDscr
from .CharacteristicUserDescriptionDscr import CharacteristicUserDescriptionDscr

class TestChrc(Characteristic):
  """
  Dummy test characteristic. Allows writing arbitrary bytes to its value, and
  contains "extended properties", as well as a test descriptor.

  """
  TEST_CHRC_UUID = '12345678-1234-5678-1234-56789abcdef1'

  def __init__(self, bus, index, service):
    Characteristic.__init__(
            self, bus, index,
            self.TEST_CHRC_UUID,
            ['read', 'write', 'writable-auxiliaries'],
            service)
    self.value = []
    self.add_descriptor(TestDscr(bus, 0, self))
    self.add_descriptor(
            CharacteristicUserDescriptionDscr(bus, 1, self))

  def ReadValue(self, options):
    print('TestCharacteristic Read: ' + repr(self.value))
    return self.value

  def WriteValue(self, value, options):
    print('TestCharacteristic Write: ' + repr(value))
    self.value = value
