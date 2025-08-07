#!/usr/bin/env python

import asyncio
import sys
import argparse
import time
import os
from typing import Dict, List, Tuple
from dataclasses import dataclass

from pitwall import PitWallClient
from pitwall.adapters import CaptureAdapter
from pitwall.events import SessionChange, Driver, SessionProgress, RaceControlMessage, TimingDatum, DriverStatusUpdate, \
                           SectorTimingDatum, SegmentTimingDatum, StintChange, QualifyingSessionProgress, DriverPositionUpdate

@dataclass
class DriverSummary:
    number: int
    broadcast_name: str
    max_stint: int
    position: int
    location: Tuple[int, int]

    def __repr__(self):
        return f"{self.broadcast_name} ({self.number})"

drivers: Dict[int, DriverSummary] = dict()
statuses = dict()
lap = 1

class Cancel(Exception):
    ...

def main():
    for i in range(20):
        if os.path.exists(args.input):
            break
        print(f"Waiting for {args.input}: {i}")
        time.sleep(1)

    if not os.path.exists(args.input):
        print(f"{args.input} didn't exist within 20 seconds")
        sys.exit(255)

    client = PitWallClient(CaptureAdapter(args.input))
    client.on_session_change(on_session_change)
    client.on_session_progress(on_session_progress)
    client.on_driver_data(init_drivers)
    client.on_race_control_update(on_race_control_update)
    client.on_timing_datum(on_timing_data)
    client.on_driver_status_update(on_driver_status_update)
    client.on_driver_position_update(on_driver_position_update)
    client.on_session_status(lambda s: print(f"Session is {s.status}"))
    client.on_stint_change(on_stint_change)
    client.on_track_status(lambda s: print(f"Track is {s.message} ({s.id})"))
    client.on_clock(lambda c: print(f"Race time is {c.remaining}"))

    try:
        asyncio.run(client.go())
    except Cancel:
        ...
        
    print(f"Segment statuses: {statuses}")

    if args.driver is None: # otherwise all other drivers will be out of order
        for i, driver in enumerate(sorted(drivers.values(), key=lambda d: d.position)):
            if driver.position != i+1:
                raise Exception(f"{driver} is out of order (should be at {i+1})")


def on_session_change(session: SessionChange) -> None:
    print(f"Now watching {session.name}: {session.part} ({session.status})")

def on_session_progress(progress: SessionProgress) -> None:
    if isinstance(progress, QualifyingSessionProgress):
        print(f"Qualifying session Q{progress.part}")
        return
    
    global lap
    lap = progress.lap
    print(f"Lap {lap}")
    
    if args.to > 0 and lap >= args.to:
        raise Cancel()

def on_race_control_update(updates: List[RaceControlMessage]) -> None:
    messages = ", ".join([x.message for x in updates])
    print(f"Race control: {messages}")

    # bug: this gets fired between qualifying sessions too
    # if messages == "CHEQUERED FLAG": # usually fired by itself
    #     raise Cancel()

def init_drivers(data: List[Driver]):
    # don't wipe out the existing data if the websocket reconnects
    # mid-session and re-fires the initial subscription data
    if len(drivers) > 0:
        return
    
    for driver in data:
        drivers[driver.number] = DriverSummary(driver.number, driver.broadcast_name, 0, 99, (0, 0))

def on_timing_data(data: TimingDatum) -> None:
    if args.driver is not None and args.driver != data.driver_id:
        return
    
    if isinstance(data, SegmentTimingDatum):
        segment: SegmentTimingDatum = data
        if segment.status > 0 and segment.status != 2052: # I don't remember what this means, but it's written on a post-it in my office somewhere
            last_location = drivers[segment.driver_id].location
            if segment.sector_id == 0 and segment.segment_id <= 1:
                drivers[segment.driver_id].location = (0, 0)
            elif last_location[0] < segment.sector_id or last_location[1] < segment.segment_id:
                drivers[segment.driver_id].location = (segment.sector_id, segment.segment_id)

        if segment.status not in statuses:
            statuses[segment.status] = f"{drivers[segment.driver_id]} at {lap}:{segment.sector_id}:{segment.segment_id}"
    elif isinstance(data, SectorTimingDatum):
        sector: SectorTimingDatum = data
        if sector.overall_fastest:
            print(f"\t{drivers[data.driver_id]} overall fastest sector {sector.sector_id} ({sector.time})")

def on_driver_status_update(update: DriverStatusUpdate):
    if args.driver is not None and args.driver != update.driver_id:
        return
    print(f"\t{drivers[update.driver_id]} stopped in sector {update.sector_id}")

def on_driver_position_update(update: DriverPositionUpdate):
    if args.driver is not None and args.driver != update.driver_id:
        return
    
    driver = drivers[update.driver_id]
    if driver.position == 99:
        driver.position = update.position
        return
    
    # TODO: refactor this when my brain has more capacity for mathing
    if abs(driver.position - update.position) == 1:
        try:
            swap_with = next(filter(lambda d: d.position == update.position, drivers.values()))
        except StopIteration:
            print(f"Can't find driver at position {update.position}")
            for d in sorted(drivers.values(), key=lambda d: d.position):
                print(f"\t{d} in {d.position}")
            raise

        print(f"\t{driver} {"overtook" if driver.position > update.position else "lost position to"} {swap_with}")
        swap_with.position = driver.position
    elif driver.position > update.position: # overtake
        losses = [x for x in drivers.values() if update.position <= x.position < driver.position]
        for d in losses:
            print(f"\t{driver} overtook {d}")
            d.position += 1
    elif driver.position < update.position:
        gains = [x for x in drivers.values() if driver.position < x.position <= update.position]
        for d in gains:
            print(f"\t{driver} lost position to {d}")
            d.position -= 1

    driver.position = update.position

def on_stint_change(stint: StintChange):
    if args.driver is not None and args.driver != stint.driver_id:
        return
    elif stint.driver_id not in drivers:
        # idk that this is necessary anymore
        print(f"Stint data for unknown driver {stint.driver_id}")
        return

    if stint.stint_number > drivers[stint.driver_id].max_stint:
        print(f"{drivers[stint.driver_id]} started stint {stint.stint_number} on {stint.compound} tyres")
        drivers[stint.driver_id].max_stint = stint.stint_number
    else:
        print(f"Correction: stint {stint.stint_number} for {drivers[stint.driver_id]} is on {stint.compound} tyres")

if __name__ == "__main__":
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-f", "--from", default=0)
    parser.add_argument("-t", "--to", default=0, type=int)
    parser.add_argument("-d", "--driver", type=int)
    args = parser.parse_args()

    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        ...
