import dbus

from ..Descriptor import Descriptor

class TestSecureDscr(Descriptor):
  """
  Dummy test descriptor requiring secure connection. Returns a static value.

  """
  TEST_DESC_UUID = '12345678-1234-5678-1234-56789abcdef6'

  def __init__(self, bus, index, characteristic):
    Descriptor.__init__(
            self, bus, index,
            self.TEST_DESC_UUID,
            ['secure-read', 'secure-write'],
            characteristic)

  def ReadValue(self, options):
    return [
      dbus.Byte('T'), dbus.Byte('e'), dbus.Byte('s'), dbus.Byte('t')
    ]
