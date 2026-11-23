import abc

class Processor(abc.ABC):
    def __init__(self, target_signal: str):
        self.target_signal = target_signal
        
    @abc.abstractmethod
    def process(self, value: float) -> float:
        pass
        
    def __call__(self, signal: dict) -> dict:
        if signal.get("name") == self.target_signal:
            original_value = signal.get("value")
            try:
                if isinstance(original_value, (int, float)):
                    new_value = self.process(original_value)
                    signal["value"] = new_value
            except Exception:
                pass 
                
        return signal


class ScaleProcessor(Processor):
    """Multiplies the target signal by a factor."""
    def __init__(self, target_signal: str, factor: float):
        super().__init__(target_signal)
        self.factor = factor
        
    def process(self, value: float) -> float:
        return value * self.factor


class BiasProcessor(Processor):
    """Adds a constant offset to the target signal."""
    def __init__(self, target_signal: str, offset: float):
        super().__init__(target_signal)
        self.offset = offset
        
    def process(self, value: float) -> float:
        return value + self.offset


class FilterProcessor(Processor):
    """Moving average filter for the target signal."""
    def __init__(self, target_signal: str, window_size: int = 5):
        super().__init__(target_signal)
        self.window_size = max(1, window_size)
        self._history = []
        
    def process(self, value: float) -> float:
        self._history.append(value)
        if len(self._history) > self.window_size:
            self._history.pop(0)
        return sum(self._history) / len(self._history)
