from ..Characteristic import Characteristic
from .TestEncryptDscr import TestEncryptDscr
from .CharacteristicUserDescriptionDscr import CharacteristicUserDescriptionDscr

class TestEncryptChrc(Characteristic):
  """
  Dummy test characteristic requiring encryption.
  """
  TEST_CHRC_UUID = '12345678-1234-5678-1234-56789abcdef3'

  def __init__(self, bus, index, service):
    Characteristic.__init__(
            self, bus, index,
            self.TEST_CHRC_UUID,
            ['encrypt-read', 'encrypt-write'],
            service)
    self.value = []
    self.add_descriptor(TestEncryptDscr(bus, 2, self))
    self.add_descriptor(
            CharacteristicUserDescriptionDscr(bus, 3, self))

  def ReadValue(self, options):
    print('TestEncryptCharacteristic Read: ' + repr(self.value))
    return self.value

  def WriteValue(self, value, options):
    print('TestEncryptCharacteristic Write: ' + repr(value))
    self.value = value
