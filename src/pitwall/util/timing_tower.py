from dataclasses import dataclass
from typing import Callable, Dict, List
from colorist import Color
from pitwall.client import PitWallClient
from pitwall.events import Driver, DriverPositionUpdate
from pitwall.events.timing import LapTimingDatum, TimingDatum

@dataclass
class TimingLine:
    driver_number: int
    name: str
    position: int
    lap_time: int
    """Time of last lap"""
    interval_time: int
    """Time to the driver ahead"""
    leader_time: int
    """Time to the leader"""

    def __repr__(self):
        return f"{self.name} ({self.driver_number})"

class TimingTower:
    _client: PitWallClient
    drivers: Dict[int, TimingLine]
    results: List[TimingLine]
    _on_position_change_callbacks: List[Callable[[TimingLine], None]]

    def __init__(self, client: PitWallClient):
        self._client = client
        self._client.on_driver_data(self._on_driver_data)
        self._client.on_driver_position_update(self._on_driver_position_update)
        self._client.on_timing_datum(self._on_timing_datum)
        self.drivers = dict()
        self._on_position_change_callbacks = list()

    def on_position_change(self, callback: Callable[[TimingLine], None]):
        self._on_position_change_callbacks.append(callback)

    def _on_driver_data(self, data: List[Driver]):
        if len(self.drivers) > 0:
            return
        
        for driver in data:
            self.drivers[driver.number] = TimingLine(driver.number, driver.broadcast_name, 99, 0, 0, 0)

    def _call_position_update_callbacks(self, line: TimingLine):
        for callback in self._on_position_change_callbacks:
            callback(line)

    def _on_driver_position_update(self, update: DriverPositionUpdate):
        driver = self.drivers[update.driver_id]
        if driver.position == 99:
            driver.position = update.position
            return

        # TODO: refactor this when my brain has more capacity for mathing
        if abs(driver.position - update.position) == 1:
            try:
                swap_with = next(filter(lambda d: d.position == update.position, self.drivers.values()))
            except StopIteration:
                raise Exception(f"Can't find driver at position {update.position}")
                #for d in sorted(self.drivers.values(), key=lambda d: d.position):
                #    print(f"\t{d} in {d.position}")

            print(f"{Color.MAGENTA}\t{driver} {"overtook" if driver.position > update.position else "lost position to"} {swap_with}{Color.OFF}")
            swap_with.position = driver.position
            self._call_position_update_callbacks(swap_with)
        elif driver.position > update.position: # overtake
            losses = [x for x in self.drivers.values() if update.position <= x.position < driver.position]
            for d in losses:
                print(f"{Color.MAGENTA}\t{driver} overtook {d}{Color.OFF}")
                d.position += 1
                self._call_position_update_callbacks(d)

        elif driver.position < update.position:
            gains = [x for x in self.drivers.values() if driver.position < x.position <= update.position]
            for d in gains:
                print(f"{Color.MAGENTA}\t{driver} lost position to {d}{Color.OFF}")
                d.position -= 1
                self._call_position_update_callbacks(d)

        driver.position = update.position
        self._call_position_update_callbacks(driver)
        self.results = list(sorted(self.drivers.values(), key=lambda d: d.position))
    
    def _on_timing_datum(self, datum: TimingDatum):
        if isinstance(datum, LapTimingDatum):
            self.drivers[datum.driver_id].lap_time = datum.time