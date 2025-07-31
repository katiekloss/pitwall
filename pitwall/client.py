from dataclasses import dataclass
from typing import List
from pitwall.adapters.abstract import PitWallAdapter
from collections.abc import Callable

@dataclass
class SessionChange:
    name: str
    part: str
    status: str

class PitWallClient:
    update_callbacks: List[Callable[[Update], None]]
    session_change_callbacks: List[Callable[[SessionChange], None]]

    def __init__(self, adapter : PitWallAdapter):
        self.adapter = adapter

    async def start(self) -> None:
        await self.adapter.start()

    async def stop(self) -> None:
        await self.adapter.stop()

    def on_session_change(self, session_change_callback: Callable[[SessionChange], None]):
        self.session_change_callbacks.append(session_change_callback)

    def update(self, update: Update):
        for callback in self.update_callbacks:
            callback(update)
        