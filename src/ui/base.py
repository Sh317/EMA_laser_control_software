from abc import ABC, abstractmethod

class GUI(ABC):
    @abstractmethod
    def setup_ui(self):
        pass