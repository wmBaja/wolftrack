from ..Characteristic import Characteristic
from .TestSecureDscr import TestSecureDscr
from .CharacteristicUserDescriptionDscr import CharacteristicUserDescriptionDscr

class TestSecureChrc(Characteristic):
  """
  Dummy test characteristic requiring secure connection.
  """
  TEST_CHRC_UUID = '12345678-1234-5678-1234-56789abcdef5'

  def __init__(self, bus, index, service):
    Characteristic.__init__(
            self, bus, index,
            self.TEST_CHRC_UUID,
            ['secure-read', 'secure-write'],
            service)
    self.value = []
    self.add_descriptor(TestSecureDscr(bus, 2, self))
    self.add_descriptor(
            CharacteristicUserDescriptionDscr(bus, 3, self))

  def ReadValue(self, options):
    print('TestSecureCharacteristic Read: ' + repr(self.value))
    return self.value

  def WriteValue(self, value, options):
    print('TestSecureCharacteristic Write: ' + repr(value))
    self.value = value
