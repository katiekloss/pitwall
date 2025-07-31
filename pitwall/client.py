from typing import List
import warnings
from pitwall.adapters.abstract import PitWallAdapter, Update
from pitwall.events import SessionChange
from collections.abc import Callable

class PitWallClient:
    update_callbacks: List[Callable[[Update], None]]
    session_change_callbacks: List[Callable[[SessionChange], None]]

    def __init__(self, adapter : PitWallAdapter):
        self.adapter = adapter
        self.update_callbacks = list()
        self.session_change_callbacks = list()

    async def go(self) -> None:
        async for update in self.adapter.run():
            self.update(update)

    def on_update(self, callback: Callable[[Update], None]):
        warnings.warn("Subscribe to an actual event class or just use an adapter instead of the full client", stacklevel=2)
        self.update_callbacks.append(callback)

    def on_session_change(self, session_change_callback: Callable[[SessionChange], None]):
        self.session_change_callbacks.append(session_change_callback)

    def update(self, update: Update):
        for callback in self.update_callbacks:
            callback(update)

        if update.src == "SessionInfo":
            payload = SessionChange(update.data["Meeting"]["Name"], update.data["Name"], update.data["ArchiveStatus"]["Status"])
            for callback in self.session_change_callbacks:
                callback(payload)
            