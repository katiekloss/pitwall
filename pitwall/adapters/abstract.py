from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict

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
    @abstractmethod
    async def run(self) -> AsyncIterator[Update]:
        ...
