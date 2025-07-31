from typing import Any, Dict, List
import warnings
from pitwall.adapters.abstract import PitWallAdapter, Update
from collections.abc import Callable

from pitwall.events import Driver, SessionChange, SessionProgress

class PitWallClient:
    update_callbacks: List[Callable[[Update], None]]
    session_change_callbacks: List[Callable[[SessionChange], None]]
    driver_data_callbacks: List[Callable[[List[Driver]], None]]
    session_progress_callbacks: List[Callable[[SessionProgress], None]]
    racecontrol_update_callbacks: List[Callable[[RaceControlUpdate], None]]

    def __init__(self, adapter : PitWallAdapter):
        self.adapter = adapter
        self.update_callbacks = list()
        self.session_change_callbacks = list()
        self.driver_data_callbacks = list()
        self.session_progress_callbacks = list()

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

    def on_session_progress(self, callback: Callable[[SessionProgress], None]) -> None:
        self.session_progress_callbacks.append(callback)

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
        elif update.src == "SessionData":
            # what are these for, again?
            if "Series" not in update.data or isinstance(update.data["Series"], list):
                return

            session = update.data["Series"][list(update.data["Series"].keys())[0]]
            if "Lap" in session:
                lap = int(update.data["Series"][list(update.data["Series"].keys())[0]]["Lap"])
                self.fire_callbacks(self.session_progress_callbacks, SessionProgress(lap))
            elif "QualifyingPart" in session:
                ... # TODO: fire events for Q1/2/3 instead?
            else:
                raise KeyError("Unknown SessionData format")
        elif update.src == "RaceControlMessages":
            if isinstance(update.data["Messages"], list):
                messages = update.data["Messages"]
            elif isinstance(update.data["Messages"], dict):
                messages = list(update.data["Messages"].values())

            messages = ", ".join([x["Message"] for x in messages])
            print(f"Race control: {messages}")
            
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