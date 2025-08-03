from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Dict, List

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
    update_callbacks: List[Callable[[Update], None]]

    def __init__(self):
        self.update_callbacks = list()

    def on_update(self, callback: Callable[[Update], None]):
        self.update_callbacks.append(callback)
        
    @abstractmethod
    async def run(self) -> AsyncIterator[Update]:
        ...
