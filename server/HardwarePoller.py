from threading import Thread, Event
import random

class HardwarePoller(Thread):
  def __init__(self, pollingRate, cb):
    super().__init__()
    self.pollingRate = pollingRate
    self.cb = cb
    self.stopEvent = Event()

  def run(self):
    while not self.stopEvent.wait(self.pollingRate):
      print('Polling hardware...')
      blah = random.random()
      self.cb(blah)


    print('Cleaning up hardware poller thread')
    self.cleanup()

  def cleanup(self):
    pass
