from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

class EOS(Exception):
    """Raised when the client reaches the end of the given event stream"""
    pass

@dataclass
class Update:
    """A single event consumed from the backing adapter's stream"""

    src: str
    "The event type"
    
    # TODO: make this not Any
    data: Dict[str, Any]
    "The event payload"

    ts: int
    "The time that the event was originally received, in Unix time"

class PitWallAdapter(ABC):
    message_callbacks: List[Callable[[Update], None]]

    def __init__(self):
        self.message_callbacks = list()
    
    @abstractmethod
    async def run(self) -> None:
        ...
    
    # bug: if callback doesn't match the expected signature, stuff silently blows up
    def on_message(self, callback: Callable[[Update], None]) -> None:
        self.message_callbacks.append(callback)

    def _message(self, update: Update) -> None:
        for callback in self.message_callbacks:
            # if this raises, it'll get eaten?
            callback(update)
