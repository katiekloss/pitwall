from typing import Any, Dict, List
import warnings
from pitwall.adapters.abstract import PitWallAdapter, Update
from pitwall.events import SessionChange
from collections.abc import Callable

from pitwall.events.drivers import Driver

class PitWallClient:
    update_callbacks: List[Callable[[Update], None]]
    session_change_callbacks: List[Callable[[SessionChange], None]]
    driver_data_callbacks: List[Callable[[List[Driver]], None]]

    def __init__(self, adapter : PitWallAdapter):
        self.adapter = adapter
        self.update_callbacks = list()
        self.session_change_callbacks = list()
        self.driver_data_callbacks = list()

    async def go(self) -> None:
        async for update in self.adapter.run():
            self.update(update)

    def on_update(self, callback: Callable[[Update], None]):
        warnings.warn("Subscribe to an actual event class or just use an adapter instead of the full client", stacklevel=2)
        self.update_callbacks.append(callback)

    def on_session_change(self, session_change_callback: Callable[[SessionChange], None]):
        self.session_change_callbacks.append(session_change_callback)

    def on_driver_data(self, callback: Callable[[List[Driver]], None]) -> None:
        self.driver_data_callbacks.append(callback)

    def update(self, update: Update):
        for callback in self.update_callbacks:
            callback(update)

        if update.src == "init":
            self.fire_callbacks(self.driver_data_callbacks, self.parse_drivers(update.data["DriverList"]))
            self.fire_callbacks(self.session_change_callbacks, self.parse_session(update.data["SessionInfo"]))
        elif update.src == "SessionInfo":
            self.fire_callbacks(self.session_change_callbacks, self.parse_session(update.data))
        elif update.src == "DriverList":
            self.fire_callbacks(self.driver_data_callbacks, self.parse_drivers(update.data))
            
    def fire_callbacks(self, callbacks: List[Callable[[Any], None]], payload: Any) -> None:
        for callback in callbacks:
            callback(payload)

    def parse_session(self, data: Dict[str, Any]) -> SessionChange:
        return SessionChange(data["Meeting"]["Name"], data["Name"], data["ArchiveStatus"]["Status"])
    
    def parse_drivers(self, driver_data) -> List[Driver]:
        drivers = list()
        if isinstance(driver_data, dict):
            for driver_id in driver_data.keys():
                if driver_id == "_kf": # does this rely on its order?
                    break

                if "BroadcastName" not in driver_data[driver_id]:
                    continue

                drivers.append(Driver(int(driver_id), driver_data[driver_id]["BroadcastName"]))
        else:
            for driver in driver_data:
                drivers.append(Driver(driver["RacingNumber"], driver["BroadcastName"]))
        
        return drivers