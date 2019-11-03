import dbus

from ..Characteristic import Characteristic
from .TestDscr import TestDscr
from .CharacteristicUserDescriptionDscr import CharacteristicUserDescriptionDscr
from ..dbusPaths import GATT_CHRC_IFACE

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
            ['read', 'write', 'writable-auxiliaries', 'notify'],
            service)
    self.notifying = False
    self.value = 0
    self.add_descriptor(TestDscr(bus, 0, self))
    self.add_descriptor(CharacteristicUserDescriptionDscr(bus, 1, self))

  def notifyValueChange(self):
    if not self.notifying:
      return
    arr = self.convertIntToDbusByteArray(self.value)
    self.PropertiesChanged(
            GATT_CHRC_IFACE,
            { 'Value': arr },
            [])
  
  def updateValue(self, newVal):
    self.value = newVal
    print('Updated value: ' + repr(self.value))
    
    if self.notifying:
      self.notifyValueChange()
    
    return True

  def convertIntToDbusByteArray(self, integer):
    byteArr = list(integer.to_bytes(2, byteorder='big'))
    return dbus.ByteArray(byteArr)


  def ReadValue(self, options):
    print('TestCharacteristic Read: ' + repr(self.value))
    return self.convertIntToDbusByteArray(self.value)

  def WriteValue(self, value, options):
    print('TestCharacteristic Write: ' + repr(value))
    self.value = value
    
  def StartNotify(self):
    if self.notifying:
      print('Already notifying, nothing to do')
      return

    self.notifying = True
    self.notifyValueChange()

  def StopNotify(self):
    if not self.notifying:
      print('Not notifying, nothing to do')
      return

    self.notifying = False
