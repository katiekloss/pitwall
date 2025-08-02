from typing import Any, Dict, List
import warnings
from pitwall.adapters.abstract import PitWallAdapter, Update
from collections.abc import Callable, Generator

from pitwall.events import Driver, SessionChange, SessionProgress, RaceControlUpdate, TimingDatum, DriverStatusUpdate, SectorTimingDatum, SegmentTimingDatum, SessionStatus, StintChange

class PitWallClient:
    update_callbacks: List[Callable[[Update], None]]
    session_change_callbacks: List[Callable[[SessionChange], None]]
    driver_data_callbacks: List[Callable[[List[Driver]], None]]
    session_progress_callbacks: List[Callable[[SessionProgress], None]]
    race_control_update_callbacks: List[Callable[[RaceControlUpdate], None]]
    timing_data_callbacks: List[Callable[[TimingDatum], None]]
    driver_status_update_callbacks: List[Callable[[DriverStatusUpdate], None]]
    session_status_callbacks: List[Callable[[SessionStatus], None]]
    stint_change_callbacks: List[Callable[[StintChange], None]]

    def __init__(self, adapter : PitWallAdapter):
        self.adapter = adapter
        self.update_callbacks = list()
        self.session_change_callbacks = list()
        self.driver_data_callbacks = list()
        self.session_progress_callbacks = list()
        self.race_control_update_callbacks = list()
        self.timing_data_callbacks = list()
        self.driver_status_update_callbacks = list()
        self.session_status_callbacks = list()
        self.stint_change_callbacks = list()

    async def go(self) -> None:
        async for update in self.adapter.run():
            self.update(update)

    def on_update(self, callback: Callable[[Update], None]):
        warnings.warn("Subscribe to an actual event class or use an adapter instead of the full client", stacklevel=2)
        self.update_callbacks.append(callback)

    def on_session_change(self, session_change_callback: Callable[[SessionChange], None]):
        self.session_change_callbacks.append(session_change_callback)

    def on_driver_data(self, callback: Callable[[List[Driver]], None]) -> None:
        self.driver_data_callbacks.append(callback)

    def on_session_progress(self, callback: Callable[[SessionProgress], None]) -> None:
        self.session_progress_callbacks.append(callback)

    def on_race_control_update(self, callback: Callable[[RaceControlUpdate], None]) -> None:
        self.race_control_update_callbacks.append(callback)

    def on_timing_datum(self, callback: Callable[[TimingDatum], None]) -> None:
        self.timing_data_callbacks.append(callback)

    def on_driver_status_update(self, callback: Callable[[DriverStatusUpdate], None]) -> None:
        self.driver_status_update_callbacks.append(callback)

    def on_session_status(self, callback: Callable[[SessionStatus], None]) -> None:
        self.session_status_callbacks.append(callback)

    def on_stint_change(self, callback: Callable[[StintChange], None]) -> None:
        self.stint_change_callbacks.append(callback)

    def update(self, update: Update):
        for callback in self.update_callbacks:
            callback(update)

        if update.src == "init":
            self.fire_callbacks(self.driver_data_callbacks, self.parse_drivers(update.data["DriverList"]))
            self.fire_callbacks(self.session_change_callbacks, self.parse_session(update.data["SessionInfo"]))
            self.parse_stints(update.data["TimingAppData"])
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

            # bug: messages is a list of dicts, not a list of strings
            self.fire_callbacks(self.race_control_update_callbacks, RaceControlUpdate(messages))
        elif update.src == "TimingData":
            for datum in self.handle_timing_data(update.data):
                self.fire_callbacks(self.timing_data_callbacks, datum)
        elif update.src == "SessionStatus":
            self.fire_callbacks(self.session_status_callbacks, SessionStatus(update.data["Status"]))
        elif update.src == "TimingAppData" or update.src == "TimingStats":
            self.parse_stints(update.data)

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

    def handle_timing_data(self, data) -> Generator[TimingDatum]:
        for driver_id in data["Lines"].keys():
            driver = data["Lines"][driver_id]

            if "Sectors" not in driver:
                # probably "GapToLeader" and/or "IntervalToPositionAhead" instead
                continue

            # happens at the start of the race to reset everyone, for some reason it's not a dict
            if isinstance(driver["Sectors"], list):
                driver["Sectors"] = dict([(i, x) for i, x in enumerate(driver["Sectors"])])

            for sector_id in driver["Sectors"].keys():
                sector = driver["Sectors"][sector_id]
                sector_id = int(sector_id)

                if "Stopped" in sector:
                    self.fire_callbacks(self.driver_status_update_callbacks, DriverStatusUpdate(driver_id, sector_id, True))
                    continue
                
                elif "PreviousValue" in sector:
                    continue

                overall_fastest = "OverallFastest" in sector
                personal_fastest = "PersonalFastest" in sector

                if "Segments" not in sector:
                    # print(f"\t{sector}")
                    if "Value" in sector and sector["Value"] != "":
                        # if not, I think it's JUST OverallFastest=false to clear someone's previous True?
                        yield SectorTimingDatum(driver_id, sector_id, personal_fastest, overall_fastest, float(sector["Value"]))
                    continue
                
                if isinstance(sector["Segments"], list): # same as the above one for driver[Sectors]
                    sector["Segments"] = dict([(i, x) for i, x in enumerate(sector["Segments"])])

                for segment_id in sector["Segments"].keys(): # order these?
                    segment = sector["Segments"][segment_id]
                    segment_id = int(segment_id)
                    status: int = segment["Status"]

                    yield SegmentTimingDatum(driver_id, sector_id, segment_id, status)

    def parse_stints(self, data) -> None:
        for driver_id in data["Lines"].keys():
            driver_line = data["Lines"][driver_id]
            if "Stints" in driver_line:
                for stint_number in driver_line["Stints"]:
                    if isinstance(stint_number, dict): # stint 0
                        self.fire_callbacks(self.stint_change_callbacks, StintChange(driver_id, 1, stint_number["Compound"]))
                    elif "Compound" in driver_line["Stints"][stint_number]:
                        self.fire_callbacks(self.stint_change_callbacks, StintChange(driver_id, int(stint_number) + 1, driver_line["Stints"][stint_number]["Compound"]))