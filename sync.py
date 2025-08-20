import copy
from typing import Dict
from pitwall.adapters.abstract import PitWallAdapter, Update
from pitwall.adapters.captureadapter import CaptureAdapter
from asyncio import run

from pitwall.client import PitWallClient
from pitwall.events.timing import IntervalTimingDatum, TimingDatum

class SyncAdapter(PitWallAdapter):
    _inner_adapter: PitWallAdapter
    _client: PitWallClient
    _sequence: int
    _snapshots: Dict[int, Dict[int, float]]
    _last_snapshot: Dict[int, float]

    def __init__(self, adapter: PitWallAdapter):
        super().__init__()
        self._inner_adapter = adapter
        self._inner_adapter.on_message(self._on_message)

        # Make sure that the client's callbacks are registered AFTER our own, so that we can infer
        # which client-level updates were fired by the adapter's most recently-sequenced update
        self._client = PitWallClient(self._inner_adapter)
        self._client.on_timing_datum(self._on_timing_datum)
        self._sequence = 0
        self._snapshots = dict()
        self._last_snapshot = None

    def _on_message(self, update: Update):
        self._sequence += 1

    def _on_timing_datum(self, point: TimingDatum):
        if not isinstance(point, IntervalTimingDatum):
            return
        
        if self._last_snapshot is None:
            new = dict()
        else:
            new = copy.copy(self._last_snapshot)
            
        new[point.driver_id] = point.time_to_driver_ahead
        self._snapshots[self._sequence] = new
        self._last_snapshot = new

    async def run(self):
        await self._inner_adapter.run()

async def main():
    replay = CaptureAdapter("data/2025_hungary_race.txt")
    sync = SyncAdapter(replay)
    try:
        await sync.run()
    finally:
        return sync

if __name__ == "__main__":
    sync = run(main())
    for i in sync._snapshots:
        snapshot = sync._snapshots[i]
        if 81 in snapshot and snapshot[81] == 0.687 \
                and 63 in snapshot and snapshot[63] == 21.395 \
                and 1 in snapshot and snapshot[1] == 1.228 \
                and 31 in snapshot and snapshot[31] == 2.005 \
                and 44 in snapshot and snapshot[44] == 0.550 \
                and 43 in snapshot and snapshot[43] == 0.504:
            print(f"Found matching timing samples at sequence {i}")
