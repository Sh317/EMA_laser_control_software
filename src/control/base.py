from abc import ABC, abstractmethod

class ControlLoop(ABC):
    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def lock(self):
        pass

    @abstractmethod
    def unlock(self):
        pass

    @abstractmethod
    def start_scan(self):
        pass

    @abstractmethod
    def stop(self):
        pass
