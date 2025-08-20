from typing import Any, Dict, List
from collections.abc import Callable

from pitwall.adapters.abstract import PitWallAdapter, Update
from pitwall.events import Driver, SessionChange, SessionProgress, RaceControlMessage, \
    TimingDatum, DriverStatusUpdate, SectorTimingDatum, SegmentTimingDatum, SessionStatus, \
    StintChange, TrackStatus, Clock, QualifyingSessionProgress, DriverPositionUpdate, \
    SessionConfig, LapSessionProgress
from pitwall.events.timing import LapTimingDatum

class PitWallClient:

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
    session_config_callbacks: List[Callable[[SessionConfig], None]]

    def __init__(self, adapter : PitWallAdapter):
        self.adapter = adapter
        self.adapter.on_message(self._update)

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
        self.session_config_callbacks = list()

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

    def on_session_config(self, callback: Callable[[SessionConfig], None]) -> None:
        self.session_config_callbacks.append(callback)

    def _update(self, update: Update):
        # should this be an entirely separate event, rather than a magic string?
        if update.src == "init":
            self._fire_callbacks(self.driver_data_callbacks, self._parse_drivers(update.data["DriverList"]))
            self._fire_callbacks(self.session_change_callbacks, self._parse_session(update.data["SessionInfo"]))
            self._parse_stints(update.data["TimingAppData"])
            self._parse_session_data(update.data["SessionData"])
            # sometimes it's after the initial subscribe, but in the init format
            if "RaceControlMessages" in update.data:
                self._parse_messages(update.data["RaceControlMessages"]["Messages"])
            self._parse_track_config(update.data["TimingData"])
        elif update.src == "SessionInfo":
            self._fire_callbacks(self.session_change_callbacks, self._parse_session(update.data))
        elif update.src == "DriverList":
            self._fire_callbacks(self.driver_data_callbacks, self._parse_drivers(update.data))
        elif update.src == "SessionData":
            self._parse_session_data(update.data)
        elif update.src == "RaceControlMessages":
            self._parse_messages(update.data["Messages"])
        elif update.src == "TimingData":
            self._handle_timing_data(update.data)
        elif update.src == "SessionStatus":
            self._fire_callbacks(self.session_status_callbacks, SessionStatus(update.data["Status"]))
        elif update.src == "TimingAppData" or update.src == "TimingStats":
            self._parse_stints(update.data)
        elif update.src == "TrackStatus":
            self._fire_callbacks(self.track_status_callbacks, TrackStatus(int(update.data["Status"]), update.data["Message"]))
        elif update.src == "ExtrapolatedClock":
            self._fire_callbacks(self.clock_callbacks, Clock(update.data["Remaining"]))
        # elif update.src in ["Heartbeat", "WeatherData", "TeamRadio"]:

    def _fire_callbacks(self, callbacks: List[Callable[[Any], None]], payload: Any) -> None:
        for callback in callbacks:
            callback(payload)

    def _parse_session(self, data: Dict[str, Any]) -> SessionChange:
        return SessionChange(data["Meeting"]["Name"], data["Name"], data["ArchiveStatus"]["Status"])
    
    def _parse_drivers(self, driver_data) -> List[Driver]:
        drivers = list()
        if isinstance(driver_data, dict):
            for driver_id in driver_data.keys():
                if driver_id == "_kf": # idk what this is but SignalR LOVES serializing it
                    continue

                driver: Dict = driver_data[driver_id]
                if "BroadcastName" not in driver:
                    continue

                drivers.append(Driver(int(driver_id), driver["BroadcastName"], driver.get("TeamName", None), \
                                      driver.get("TeamColour", None), driver.get("FirstName", None), driver.get("LastName", None)))
        else:
            for driver in driver_data:
                drivers.append(Driver(driver["RacingNumber"], driver["BroadcastName"], driver.get("TeamName", None),
                                      driver.get("TeamColour", None), driver.get("FirstName", None), driver.get("LastName", None)))
        
        return drivers

    def _handle_timing_data(self, data) -> None:
        """Handles TimingData, fires DriverPositionUpdate, DriverStatusUpdate, SectorTimingDatum, SegmentTimingDatum, and LapTimingDatum"""

        for driver_id in data["Lines"].keys():
            driver: Dict[str, Any] = data["Lines"][driver_id]

            if "Position" in driver:
                self._fire_callbacks(self.driver_position_update_callbacks, DriverPositionUpdate(int(driver_id), int(driver["Position"])))
                continue
                
            if "LastLapTime" in driver and "NumberOfLaps" in driver: # the latter can still be false; it won't include the lap time either
                self._fire_callbacks(self.timing_data_callbacks, LapTimingDatum(int(driver_id),
                                                                               driver["NumberOfLaps"],
                                                                               driver["LastLapTime"].get("PersonalFastest", False),
                                                                               driver["LastLapTime"].get("OverallFastest", False),
                                                                               driver["LastLapTime"]["Value"])) # bug: str, not a float
            
            if "Sectors" not in driver:
                if "Status" in driver or "Stopped" in driver:
                    self._fire_callbacks(self.driver_status_update_callbacks, DriverStatusUpdate(int(driver_id), None, driver.get("Retired", None), driver.get("Stopped", None), driver["Status"]))
                
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
                    self._fire_callbacks(self.driver_status_update_callbacks, DriverStatusUpdate(int(driver_id), sector_id + 1, False, True, None))
                    continue
                
                elif "PreviousValue" in sector:
                    continue

                overall_fastest = "OverallFastest" in sector
                personal_fastest = "PersonalFastest" in sector

                if "Segments" not in sector:
                    # print(f"\t{sector}")
                    if "Value" in sector and sector["Value"] != "":
                        # if not, I think it's JUST OverallFastest=false to clear someone's previous True?
                        self._fire_callbacks(self.timing_data_callbacks, SectorTimingDatum(int(driver_id),
                                                                                          sector_id + 1,
                                                                                          personal_fastest,
                                                                                          overall_fastest,
                                                                                          float(sector["Value"])))
                    continue
                
                if isinstance(sector["Segments"], list): # same as the above one for driver[Sectors]
                    sector["Segments"] = dict([(i, x) for i, x in enumerate(sector["Segments"])])

                for segment_id in sector["Segments"].keys(): # order these?
                    segment = sector["Segments"][segment_id]
                    segment_id = int(segment_id)
                    status: int = segment["Status"]
                    self._fire_callbacks(self.timing_data_callbacks, SegmentTimingDatum(int(driver_id), sector_id + 1, segment_id + 1, status))

    def _parse_stints(self, data) -> None:
        for driver_id in data["Lines"].keys():
            driver_line = data["Lines"][driver_id]

            if "Stints" in driver_line:
                for stint_number in driver_line["Stints"]:
                    if isinstance(stint_number, dict): # stint 0
                        self._fire_callbacks(self.stint_change_callbacks, StintChange(int(driver_id), 1, stint_number["Compound"]))
                    elif "Compound" in driver_line["Stints"][stint_number]:
                        self._fire_callbacks(self.stint_change_callbacks, StintChange(int(driver_id), int(stint_number) + 1, driver_line["Stints"][stint_number]["Compound"]))
            
            if "GridPos" in driver_line: # format in the initial subscribe
                self._fire_callbacks(self.driver_position_update_callbacks, DriverPositionUpdate(int(driver_id), int(driver_line["GridPos"])))
            elif "Line" in driver_line: # initial subscribe, qualifying edition
                self._fire_callbacks(self.driver_position_update_callbacks, DriverPositionUpdate(int(driver_id), driver_line["Line"]))
                                    
    def _parse_messages(self, messages: List[Dict[str, Any]] | Dict[str, Any]):
        def parse_message(x: Dict[str, Any]):
            return RaceControlMessage(x["Category"],
                                      x.get("Flag", None),
                                      x.get("Scope", None),
                                      x["Message"],
                                      x.get("Lap", None),
                                      x.get("Sector", None))
        
        if isinstance(messages, dict):
            # after initial subscribe, it becomes a dict keyed by a monotonic int sequence
            messages = list(messages.values())
        
        self._fire_callbacks(self.race_control_update_callbacks, [parse_message(x) for x in messages])
    
    def _parse_session_data(self, data: Dict[str, Any]) -> None:
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
            self._fire_callbacks(self.session_progress_callbacks, LapSessionProgress(lap))
        elif "QualifyingPart" in session:
            self._fire_callbacks(self.session_progress_callbacks, QualifyingSessionProgress(session["QualifyingPart"]))
        else:
            raise KeyError("Unknown SessionData format")
    
    def _parse_track_config(self, timing_data: Dict[str, Any]):
        sample = next(iter(timing_data["Lines"].values()))
        layout = {1: len(sample["Sectors"][0]["Segments"]),
                  2: len(sample["Sectors"][1]["Segments"]),
                  3: len(sample["Sectors"][2]["Segments"])}
        self._fire_callbacks(self.session_config_callbacks, SessionConfig(layout))