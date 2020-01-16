import array

from ..Descriptor import Descriptor
from ..errors import NotPermittedException

class CharacteristicUserDescriptionDscr(Descriptor):
  """
  Writable CUD descriptor.

  """
  CUD_UUID = '2901'

  def __init__(self, bus, index, characteristic):
    self.writable = 'writable-auxiliaries' in characteristic.flags
    self.value = array.array('B', b'This is a characteristic for testing')
    self.value = self.value.tolist()
    Descriptor.__init__(
            self, bus, index,
            self.CUD_UUID,
            ['read', 'write'],
            characteristic)

  def ReadValue(self, options):
    return self.value

  def WriteValue(self, value, options):
    if not self.writable:
      raise NotPermittedException()
    self.value = value

