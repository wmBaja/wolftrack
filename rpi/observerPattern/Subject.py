class Subject():
  """
  A Subject in the Observer design pattern. Sends updates about its internal
  status to Observers that are attached to it.
  """
  def __init__(self):
    """
    Initializes an empty list of observers.
    """
    self._observers = []

  def attach(self, observer):
    """
    Adds the given observer to the list of observers to receive updates if it
    is not already in the list.
    Returns True if the observer is added to the list and False if not.
    """
    if observer not in self._observers:
      self._observers.append(observer)
      return True
    return False

  def detach(self, observer):
    """
    Removes the given observer from the list of observers if it is in the list.
    Returns True if the observer is removed and False if not.
    """
    try:
      self._observers.remove(observer)
      return True
    except ValueError:
      return False

  def notify(self, updates):
    """
    Notifies all observers of the given updates.
    """
    for observer in self._observers:
      observer.update(updates)
