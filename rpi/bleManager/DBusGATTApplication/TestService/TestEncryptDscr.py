import dbus

from ..Descriptor import Descriptor

class TestEncryptDscr(Descriptor):
  """
  Dummy test descriptor requiring encryption. Returns a static value.
  """
  TEST_DESC_UUID = '12345678-1234-5678-1234-56789abcdef4'

  def __init__(self, bus, index, characteristic):
    Descriptor.__init__(
            self, bus, index,
            self.TEST_DESC_UUID,
            ['encrypt-read', 'encrypt-write'],
            characteristic)

  def ReadValue(self, options):
    return [
      dbus.Byte('T'), dbus.Byte('e'), dbus.Byte('s'), dbus.Byte('t')
    ]