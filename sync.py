import asyncio
import copy
import logging
from typing import Dict
from asyncio import run, gather

from pitwall.client import PitWallClient
from pitwall.events.timing import IntervalTimingDatum, TimingDatum
from pitwall.adapters.abstract import PitWallAdapter, Update
from pitwall.adapters.captureadapter import CaptureAdapter
from replay import BufferingAdapter, RealtimeReplayAdapter

logging.basicConfig(
    format="%(asctime)s %(name)s: %(message)s",
    level=logging.DEBUG,
)

class SyncClient:
    _adapter: BufferingAdapter
    _client: PitWallClient
    _sequence: int
    _snapshots: Dict[int, Dict[int, float]]
    _last_snapshot: Dict[int, float]

    def __init__(self, adapter: BufferingAdapter):
        super().__init__()
        self._adapter = adapter
        self._adapter.on_message(self._inner_message)

        # Make sure that the client's callbacks are registered AFTER our own, so that we can infer
        # which client-level updates were fired by the adapter's most recently-sequenced update
        self._client = PitWallClient(self._adapter)
        self._client.on_timing_datum(self._on_timing_datum)

        self._sequence = 0
        self._snapshots = dict()
        self._last_snapshot = None

    def _inner_message(self, u: Update):
        self._sequence = u.seq

    def _on_timing_datum(self, point: TimingDatum):
        if not isinstance(point, IntervalTimingDatum):
            return
        
        if self._last_snapshot is None:
            new = dict()
        else:
            new = copy.copy(self._last_snapshot)
            
        new[point.driver_id] = point.time_to_driver_ahead
        # if multiple timing updates fired from a single message, this will overwrite the previous update
        # and be eventually consistent with the contents of the message (but is probably inefficient until then)
        self._snapshots[self._sequence] = new
        self._last_snapshot = new

    async def run(self):
        await self._client.go()

    def find(self, intervals: Dict[int, float]) -> int:
        print(f"Examining {len(self._snapshots)} snapshots")
        for sequence, snapshot in self._snapshots.items():
            mismatches = [driver_id not in snapshot or snapshot[driver_id] != intervals[driver_id] for driver_id in intervals]
            if not any(mismatches):
                return sequence

async def sync_to():
    while len(sync._adapter._history) < 66130:
        await asyncio.sleep(1)

    seq = sync.find({81: 0.687,
             63: 21.395,
             1: 1.228,
             31: 2.005,
             44: 0.550,
             43: 0.504})
    print(f"Found match at sequence {seq}")
    (to_replay, new_adapter) = await sync._adapter.resume_from(seq)
    print(f"{len(to_replay)} updates to replay, {new_adapter._queue.qsize()} waiting")
    new_client = PitWallClient(RealtimeReplayAdapter(new_adapter))
    for msg in to_replay:
        await new_client._update(msg)
    delay = (sync._adapter._last_message.ts - to_replay[-1].ts) / 1000000000
    print(f"We are {delay:.03f}s behind")
    await new_client.go()
    
async def main():
    global sync

    buffer = BufferingAdapter(CaptureAdapter("data/2025_hungary_race.txt"))
    sync = SyncClient(buffer)

    await gather(sync.run(), sync_to())
    
if __name__ == "__main__":
    run(main())