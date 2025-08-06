from typing import Any, Dict, List
from collections.abc import Callable, Generator

from pitwall.adapters.abstract import PitWallAdapter, Update
from pitwall.events import Driver, SessionChange, SessionProgress, RaceControlMessage, \
    TimingDatum, DriverStatusUpdate, SectorTimingDatum, SegmentTimingDatum, SessionStatus, \
    StintChange, TrackStatus, Clock, QualifyingSessionProgress, DriverPositionUpdate

class PitWallClient:
    update_callbacks: List[Callable[[Update], None]]
    session_change_callbacks: List[Callable[[SessionChange], None]]
    driver_data_callbacks: List[Callable[[List[Driver]], None]]
    session_progress_callbacks: List[Callable[[SessionProgress], None]]
    race_control_update_callbacks: List[Callable[[List[RaceControlMessage]], None]]
    timing_data_callbacks: List[Callable[[TimingDatum], None]]
    driver_status_update_callbacks: List[Callable[[DriverStatusUpdate], None]]
    driver_position_update_callbacks: List[Callable[[DriverPositionUpdate], None]]
    session_status_callbacks: List[Callable[[SessionStatus], None]]
    stint_change_callbacks: List[Callable[[StintChange], None]]
    track_status_callbacks: List[Callable[[TrackStatus], None]]
    clock_callbacks: List[Callable[[Clock], None]]

    def __init__(self, adapter : PitWallAdapter):
        self.adapter = adapter
        self.adapter.on_message(self.update)

        self.update_callbacks = list()
        self.session_change_callbacks = list()
        self.driver_data_callbacks = list()
        self.session_progress_callbacks = list()
        self.race_control_update_callbacks = list()
        self.timing_data_callbacks = list()
        self.driver_status_update_callbacks = list()
        self.driver_position_update_callbacks = list()
        self.session_status_callbacks = list()
        self.stint_change_callbacks = list()
        self.track_status_callbacks = list()
        self.clock_callbacks = list()

    async def go(self) -> None:
        await self.adapter.run()

    def on_session_change(self, session_change_callback: Callable[[SessionChange], None]):
        self.session_change_callbacks.append(session_change_callback)

    def on_driver_data(self, callback: Callable[[List[Driver]], None]) -> None:
        self.driver_data_callbacks.append(callback)

    def on_session_progress(self, callback: Callable[[SessionProgress], None]) -> None:
        self.session_progress_callbacks.append(callback)

    def on_race_control_update(self, callback: Callable[[List[RaceControlMessage]], None]) -> None:
        self.race_control_update_callbacks.append(callback)

    def on_timing_datum(self, callback: Callable[[TimingDatum], None]) -> None:
        self.timing_data_callbacks.append(callback)

    def on_driver_status_update(self, callback: Callable[[DriverStatusUpdate], None]) -> None:
        self.driver_status_update_callbacks.append(callback)

    def on_driver_position_update(self, callback: Callable[[DriverPositionUpdate], None]) -> None:
        self.driver_position_update_callbacks.append(callback)

    def on_session_status(self, callback: Callable[[SessionStatus], None]) -> None:
        self.session_status_callbacks.append(callback)

    def on_stint_change(self, callback: Callable[[StintChange], None]) -> None:
        self.stint_change_callbacks.append(callback)
    
    def on_track_status(self, callback: Callable[[TrackStatus], None]) -> None:
        self.track_status_callbacks.append(callback)

    def on_clock(self, callback: Callable[[Clock], None]) -> None:
        self.clock_callbacks.append(callback)

    def update(self, update: Update):
        for callback in self.update_callbacks:
            callback(update)

        # should this be an entirely separate event, rather than a magic string?
        if update.src == "init":
            self.fire_callbacks(self.driver_data_callbacks, self.parse_drivers(update.data["DriverList"]))
            self.fire_callbacks(self.session_change_callbacks, self.parse_session(update.data["SessionInfo"]))
            self.parse_stints(update.data["TimingAppData"])
            self.parse_session_data(update.data["SessionData"])
            # sometimes it's after the initial subscribe, but in the init format
            if "RaceControlMessages" in update.data:
                self.parse_messages(update.data["RaceControlMessages"]["Messages"])
        elif update.src == "SessionInfo":
            self.fire_callbacks(self.session_change_callbacks, self.parse_session(update.data))
        elif update.src == "DriverList":
            self.fire_callbacks(self.driver_data_callbacks, self.parse_drivers(update.data))
        elif update.src == "SessionData":
            self.parse_session_data(update.data)
        elif update.src == "RaceControlMessages":
            self.parse_messages(update.data["Messages"])
        elif update.src == "TimingData":
            for datum in self.handle_timing_data(update.data):
                self.fire_callbacks(self.timing_data_callbacks, datum)
        elif update.src == "SessionStatus":
            self.fire_callbacks(self.session_status_callbacks, SessionStatus(update.data["Status"]))
        elif update.src == "TimingAppData" or update.src == "TimingStats":
            self.parse_stints(update.data)
        elif update.src == "TrackStatus":
            self.fire_callbacks(self.track_status_callbacks, TrackStatus(int(update.data["Status"]), update.data["Message"]))
        elif update.src == "ExtrapolatedClock":
            self.fire_callbacks(self.clock_callbacks, Clock(update.data["Remaining"]))
        # elif update.src in ["Heartbeat", "WeatherData", "TeamRadio"]:

    def fire_callbacks(self, callbacks: List[Callable[[Any], None]], payload: Any) -> None:
        for callback in callbacks:
            callback(payload)

    def parse_session(self, data: Dict[str, Any]) -> SessionChange:
        return SessionChange(data["Meeting"]["Name"], data["Name"], data["ArchiveStatus"]["Status"])
    
    def parse_drivers(self, driver_data) -> List[Driver]:
        drivers = list()
        if isinstance(driver_data, dict):
            for driver_id in driver_data.keys():
                if driver_id == "_kf": # idk what this is but SignalR LOVES serializing it
                    continue

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

            if "Position" in driver:
                self.fire_callbacks(self.driver_position_update_callbacks, DriverPositionUpdate(int(driver_id), int(driver["Position"])))
                return
            elif "Sectors" not in driver:
                # print(driver)
                # probably "GapToLeader" and/or "IntervalToPositionAhead" instead
                continue

            # happens at the start of the race to reset everyone, for some reason it's not a dict
            if isinstance(driver["Sectors"], list):
                driver["Sectors"] = dict([(i, x) for i, x in enumerate(driver["Sectors"])])

            for sector_id in driver["Sectors"].keys():
                sector = driver["Sectors"][sector_id]
                sector_id = int(sector_id)

                if "Stopped" in sector:
                    self.fire_callbacks(self.driver_status_update_callbacks, DriverStatusUpdate(int(driver_id), sector_id, True))
                    continue
                
                elif "PreviousValue" in sector:
                    continue

                overall_fastest = "OverallFastest" in sector
                personal_fastest = "PersonalFastest" in sector

                if "Segments" not in sector:
                    # print(f"\t{sector}")
                    if "Value" in sector and sector["Value"] != "":
                        # if not, I think it's JUST OverallFastest=false to clear someone's previous True?
                        yield SectorTimingDatum(int(driver_id), sector_id, personal_fastest, overall_fastest, float(sector["Value"]))
                    continue
                
                if isinstance(sector["Segments"], list): # same as the above one for driver[Sectors]
                    sector["Segments"] = dict([(i, x) for i, x in enumerate(sector["Segments"])])

                for segment_id in sector["Segments"].keys(): # order these?
                    segment = sector["Segments"][segment_id]
                    segment_id = int(segment_id)
                    status: int = segment["Status"]

                    yield SegmentTimingDatum(int(driver_id), sector_id, segment_id, status)

    def parse_stints(self, data) -> None:
        for driver_id in data["Lines"].keys():
            driver_line = data["Lines"][driver_id]
            if "Stints" in driver_line:
                for stint_number in driver_line["Stints"]:
                    if isinstance(stint_number, dict): # stint 0
                        self.fire_callbacks(self.stint_change_callbacks, StintChange(int(driver_id), 1, stint_number["Compound"]))
                    elif "Compound" in driver_line["Stints"][stint_number]:
                        self.fire_callbacks(self.stint_change_callbacks, StintChange(int(driver_id), int(stint_number) + 1, driver_line["Stints"][stint_number]["Compound"]))
            elif "GridPos" in driver_line: # format in the initial subscribe
                self.fire_callbacks(self.driver_position_update_callbacks, DriverPositionUpdate(int(driver_id), int(driver_line["GridPos"])))
            elif "Line" in driver_line: # initial subscribe, qualifying edition
                self.fire_callbacks(self.driver_position_update_callbacks, DriverPositionUpdate(int(driver_id), driver_line["Line"]))
                                    
    def parse_messages(self, messages: List[Dict[str, Any]] | Dict[str, Any]):
        def parse_message(x: Dict[str, Any]):
            message = RaceControlMessage(x["Category"], None, None, x["Message"], None, None)
            if "Lap" in x:
                message.lap = x["Lap"]
            if "Sector" in x:
                message.sector = x["Sector"]
            if "Flag" in x:
                message.flag = x["Flag"]
            if "Scope" in x:
                message.scope = x["Scope"]
            return message
        
        if isinstance(messages, dict):
            # after initial subscribe, it becomes a dict keyed by a monotonic int sequence
            messages = list(messages.values())
        
        self.fire_callbacks(self.race_control_update_callbacks, [parse_message(x) for x in messages])
    
    def parse_session_data(self, data: Dict[str, Any]) -> None:
        if "Series" not in data or len(data["Series"]) == 0:
            # usually contains StatusSeries instead, which I don't know the meaning of
            return
        
        # sometimes you get two QualifyingPart entries, 0 and 1, so use the last one
        if isinstance(data["Series"], list):
            session = data["Series"][-1]
        else:
            session = list(data["Series"].values())[-1]

        if "Lap" in session:
            lap = int(session["Lap"])
            self.fire_callbacks(self.session_progress_callbacks, SessionProgress(lap))
        elif "QualifyingPart" in session:
            self.fire_callbacks(self.session_progress_callbacks, QualifyingSessionProgress(session["QualifyingPart"]))
        else:
            raise KeyError("Unknown SessionData format")