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
        self._client.on_driver_data(self._on_driver_data)

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

    def _on_driver_data(self, data):
        if not any(data): # this seems to happen way more often than it should
            return

        global driver_ids
        driver_ids = dict([(x.initials, x.number) for x in data])

    async def run(self):
        await self._client.go()

    def find(self, intervals: Dict[str, float]) -> int:
        print(f"Searching {len(self._snapshots)} snapshots")

        most_matches = 0
        best_sequence = None

        for sequence, snapshot in self._snapshots.items():
            matches = [True for driver_id in intervals.keys() if driver_id in snapshot and snapshot[driver_id] == intervals[driver_id]]
            if len(matches) > most_matches:
                most_matches = len(matches)
                best_sequence = sequence

            if most_matches == len(intervals):
                break

        return (best_sequence, most_matches)

async def sync_to():
    # Maybe replace with a .running property
    while len(sync._adapter._history) < 66130:
        print(f"Read to {sync._sequence}")
        await asyncio.sleep(1)

    print(f"Read to {sync._sequence}")
    constrained_sample = dict([(driver_ids[initials], sample[initials]) for initials in sample.keys() if initials in driver_ids])
    (seq, matches) = sync.find(constrained_sample)
    if seq is None:
        raise Exception("No match found")

    print(f"Found match at sequence {seq} with {matches} of {len(constrained_sample)} matching points")

    # consists of a list of updates received prior to the provided sequence
    # and a new adapter that already contains
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
    global sample

    import re
    import easyocr
    reader = easyocr.Reader(['en'])
    results = reader.readtext('test/PXL_20251006_224819827.MP_preview.jpeg')
    result = " ".join([x[1] for x in results])
    print(result)
    sample = {}

    # find things that look like this: PIA +2.806
    # try to account for whitespace (either actually recognized or added between the results)
    for group in re.findall(r"([A-Z ]{3,})\+\s*([0-9]{1,2}[.,][0-9]*)", result):
        driver = group[0].strip(' ')
        time = float(re.sub(',', '.', group[1].strip(' ')))
        sample[driver] = time

    buffer = BufferingAdapter(CaptureAdapter("data/2025_hungary_race.txt"))
    sync = SyncClient(buffer)

    await gather(sync.run(), sync_to())

if __name__ == "__main__":
    run(main())
