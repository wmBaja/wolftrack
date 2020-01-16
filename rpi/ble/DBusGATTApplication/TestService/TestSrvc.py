from ..Service import Service
from .TestChrc import TestChrc
from .TestSecureChrc import TestSecureChrc

class TestSrvc(Service):
  """
  Dummy test service that provides characteristics and descriptors that
  exercise various API functionality.

  """
  TEST_SVC_UUID = '12345678-1234-5678-1234-56789abcdef0'

  def __init__(self, bus, index):
    Service.__init__(self, bus, index, self.TEST_SVC_UUID, True)
    self.add_characteristic(TestChrc(bus, 0, self))
    self.add_characteristic(TestSecureChrc(bus, 1, self))
    
  def updateTestCharacteristic(self, value):
    testChrc = self.characteristics[0]
    testChrc.updateValue(value)
