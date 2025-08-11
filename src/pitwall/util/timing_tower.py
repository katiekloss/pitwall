from dataclasses import dataclass
from typing import Dict, List
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

    def __init__(self, client: PitWallClient):
        self._client = client
        self._client.on_driver_data(self._on_driver_data)
        self._client.on_driver_position_update(self._on_driver_position_update)
        self._client.on_timing_datum(self._on_timing_datum)
        self.drivers = dict()

    def _on_driver_data(self, data: List[Driver]):
        if len(self.drivers) > 0:
            return
        
        for driver in data:
            self.drivers[driver.number] = TimingLine(driver.number, driver.broadcast_name, 99, 0, 0, 0)

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
                print(f"Can't find driver at position {update.position}")
                for d in sorted(self.drivers.values(), key=lambda d: d.position):
                    print(f"\t{d} in {d.position}")
                raise

            print(f"\t{driver} {"overtook" if driver.position > update.position else "lost position to"} {swap_with}")
            swap_with.position = driver.position
        elif driver.position > update.position: # overtake
            losses = [x for x in self.drivers.values() if update.position <= x.position < driver.position]
            for d in losses:
                print(f"\t{driver} overtook {d}")
                d.position += 1
        elif driver.position < update.position:
            gains = [x for x in self.drivers.values() if driver.position < x.position <= update.position]
            for d in gains:
                print(f"\t{driver} lost position to {d}")
                d.position -= 1

        driver.position = update.position
    
    def _on_timing_datum(self, datum: TimingDatum):
        if isinstance(datum, LapTimingDatum):
            self.drivers[datum.driver_id].lap_time = datum.time