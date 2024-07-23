from abc import ABC, abstractmethod

class PitWallAdapter(ABC):
    @abstractmethod
    async def start(self):
        ...

