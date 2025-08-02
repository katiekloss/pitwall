#!/usr/bin/env python
import asyncio
import sys
import argparse
import time
import os
from typing import List
from dataclasses import dataclass

from pitwall import PitWallClient
from pitwall.adapters import CaptureAdapter
from pitwall.adapters.abstract import Update
from pitwall.events import SessionChange, Driver, SessionProgress, RaceControlUpdate, TimingDatum, DriverStatusUpdate, SectorTimingDatum, SegmentTimingDatum

drivers = dict()
statuses = dict()
locations = dict()
sector_leaders = dict()
lap = 1

@dataclass
class DriverSummary:
    number: int
    broadcast_name: str
    max_stint: int

    def __repr__(self):
        return f"{self.broadcast_name} ({self.number})"

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
    client.on_update(on_line)
    client.on_session_change(on_session_change)
    client.on_session_progress(on_session_progress)
    client.on_driver_data(init_drivers)
    client.on_race_control_update(on_race_control_update)
    client.on_timing_datum(on_timing_data)
    client.on_driver_status_update(on_driver_status_update)
    client.on_session_status(lambda s: print(f"Session is {s.status}"))

    try:
        asyncio.run(client.go())
    except Cancel:
        ...
        
    print(f"Segment statuses: {statuses}")

def on_session_change(session: SessionChange) -> None:
    change_session(session)

def on_session_progress(progress: SessionProgress) -> None:
    global lap
    lap = progress.lap
    print(f"Lap {lap}")

def on_race_control_update(update: RaceControlUpdate) -> None:
    messages = ", ".join([x["Message"] for x in update.messages])
    print(f"Race control: {messages}")

    if messages == "CHEQUERED FLAG": # usually fired by itself
        raise Cancel()

def on_line(update: Update):
    src = update.src
    data = update.data

    if args.to > 0 and lap >= args.to:
        print(f"Reached lap {lap}")
        return

    if src == "TimingAppData" or src == "TimingStats":
        for driver_id in data["Lines"].keys():
            if args.driver is not None and args.driver != driver_id:
                continue

            if driver_id not in drivers:
                print(f"Timing data for unknown driver {driver_id}")
                continue
            driver_line = data["Lines"][driver_id]
            if "Stints" in driver_line:
                print(driver_line["Stints"])
                for stint_number in driver_line["Stints"]:
                    if isinstance(stint_number, dict): # stint 0
                        drivers[driver_id].max_stint = 0
                        continue
                    elif int(stint_number) > drivers[driver_id].max_stint:
                        drivers[driver_id].max_stint = int(stint_number)
                        print(f"{drivers[driver_id]} started stint {stint_number}")
                    # stint = driver_line["Stints"][stint_number]
    elif src == "TrackStatus":
        message = data["Message"]
        status = data["Status"]
        print(f"Track is {message} ({status})")
    elif src == "ExtrapolatedClock":
        t = data["Remaining"]
        print(f"Race time is {t}")
    elif src in ["Heartbeat", "WeatherData", "TeamRadio"]:
        ...

def change_session(session: SessionChange):
    print(f"Now watching {session.name}: {session.part} ({session.status})")

def init_drivers(data: List[Driver]):
    for driver in data:
        drivers[str(driver.number)] = DriverSummary(driver.number, driver.broadcast_name, 1)

def on_timing_data(data: TimingDatum) -> None:
    if args.driver is not None and args.driver != data.driver_id:
        return
    
    if isinstance(data, SegmentTimingDatum):
        segment: SegmentTimingDatum = data
        if segment.status > 0 and segment.status != 2052: # I don't remember what this means, but it's written on a post-it in my office somewhere
            if segment.driver_id in locations:
                last_location = locations[segment.driver_id]
                if segment.sector_id == 0 and segment.segment_id <= 1:
                    locations[segment.driver_id] = (0, 0)
                elif last_location[0] < segment.sector_id or last_location[1] < segment.segment_id:
                    locations[segment.driver_id] = (segment.sector_id, segment.segment_id)
            else:
                locations[segment.driver_id] = (segment.sector_id, segment.segment_id)

        if segment.status not in statuses:
            statuses[segment.status] = f"{drivers[segment.driver_id]} at {lap}:{segment.sector_id}:{segment.segment_id}"
    elif isinstance(data, SectorTimingDatum):
        sector: SectorTimingDatum = data
        if sector.overall_fastest:
            if sector.sector_id not in sector_leaders or sector_leaders[sector.sector_id] != data.driver_id:
                print(f"\t{drivers[data.driver_id]} overall fastest sector {sector.sector_id} ({sector.time})")
                sector_leaders[sector.sector_id] = data.driver_id
        #elif sector.personal_fastest:
        #    print(f"\t{drivers[data.driver_id]} personal fastest sector {sector.sector_id} ({sector.time})")

def on_driver_status_update(update: DriverStatusUpdate):
    if args.driver is not None and args.driver != update.driver_id:
        return
    print(f"\t{update.driver_id} stopped in sector {update.sector_id}")

if __name__ == "__main__":
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-f", "--from", default=0)
    parser.add_argument("-t", "--to", default=0, type=int)
    parser.add_argument("-d", "--driver")
    args = parser.parse_args()

    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        ...
