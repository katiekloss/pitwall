from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List

class EOS(Exception):
    """Raised when the client reaches the end of the given event stream"""
    pass

@dataclass
class Update:
    """A single event consumed from the backing adapter's stream"""

    src: str
    "The event type"
    
    data: Dict[str, Any]
    "The event payload"

    ts: int
    "The time that the event was originally received, in Unix time"

class PitWallAdapter(ABC):
    on_update_callbacks : List[Callable[[Update], None]]

    @abstractmethod
    async def start(self):
        ...

    @abstractmethod
    async def stop(self):
        ...

    def on_update(self, update_callback: Callable[[Update], None]):
        self.on_update_callbacks.append(update_callback)