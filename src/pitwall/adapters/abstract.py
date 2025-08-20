from abc import ABC, abstractmethod
from asyncio import gather
from dataclasses import dataclass
from typing import Any, Awaitable, Coroutine, Dict, List

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
    message_callbacks: List[Awaitable[Update]]
    last_sequence: int

    def __init__(self):
        self.message_callbacks = list()
        self.last_sequence = 0
    
    @abstractmethod
    async def run(self) -> None:
        ...
    
    # bug: if callback doesn't match the expected signature, stuff silently blows up
    def on_message(self, callback: Awaitable[Update]) -> None:
        self.message_callbacks.append(callback)

    async def _message(self, update: Update):
        update.seq = self.last_sequence
        self.last_sequence += 1
        futures = list()
        for callback in self.message_callbacks:
            # if this raises, it'll get eaten?
            future = callback(update)
            if not isinstance(future, Coroutine):
                continue
            futures.append(future)
        gather(*futures)