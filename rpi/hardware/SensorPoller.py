from threading import Thread, Event

class SensorPoller(Thread):
  def __init__(self, pollingRate, callback):
    super().__init__()
    self.pollingRate = pollingRate
    self.cb = callback
    self.stopEvent = Event()

  def run(self):
    """
    Calls the poll() method on an interval defined by the polling rate and
    passes the returned value to the callback function. Calls the cleanup()
    method after the stop event is set.
    """
    if self.pollingRate == 0:
      while True:
        self.cb(self.poll())
    else:
      while not self.stopEvent.wait(self.pollingRate):
        self.cb(self.poll())
    self.cleanup()

  def poll(self):
    """
    Abstract method; this should be defined by the child class
    """
    pass

  def cleanup(self):
    """
    Abstract method; this should be defined by the child class
    """
    pass
