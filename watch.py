#!/usr/bin/env python

import asyncio
import sys
import argparse
import time
import os
import logging

from typing import Dict, List, Tuple
from dataclasses import dataclass
from colorist import Color
from pysignalr.client import SignalRClient

from pitwall import PitWallClient
from pitwall.adapters import CaptureAdapter
from pitwall.adapters.websocketadapter import WebsocketAdapter
from pitwall.adapters.rabbitadapter import RabbitAdapter
from pitwall.events import SessionChange, Driver, SessionProgress, RaceControlMessage, TimingDatum, DriverStatusUpdate, \
                           SectorTimingDatum, SegmentTimingDatum, StintChange, QualifyingSessionProgress, \
                           LapTimingDatum, SessionStatus, SessionConfig
from pitwall.util import TimingTower

logging.basicConfig(
    format="%(asctime)s %(name)s: %(message)s",
    level=logging.INFO,
)

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
segment_statuses: Dict[int, str] = dict()
driver_statuses_quick: Dict[int, str] = dict()
driver_statuses: Dict[int, int] = dict()
lap = 1
track_layout = {1: 0, 2: 0, 3: 0}
timing_tower: TimingTower

class Cancel(Exception):
    ...

def driver_filter(func):
    def wrapper(obj):
        if args.driver is not None and obj.driver_id != args.driver:
            return
        
        func(obj)
    return wrapper

def main():
    global timing_tower

    # TODO: guess what
    if str.startswith(args.input, "ws://") or str.startswith(args.input, "wss://"):
        adapter = WebsocketAdapter(SignalRClient(args.input))
    elif str.startswith(args.input, "amqp://") or str.startswith(args.input, "amqps://"):
        adapter = RabbitAdapter(args.input)
    else:
        if args.input != "-":
            for i in range(20):
                if os.path.exists(args.input):
                    break
                print(f"Waiting for {args.input}: {i}")
                time.sleep(1)

            if not os.path.exists(args.input):
                print(f"{args.input} didn't exist within 20 seconds")
                sys.exit(255)
        adapter = CaptureAdapter(args.input)
    
    client = PitWallClient(adapter)
    client.on_session_change(on_session_change)
    client.on_session_progress(on_session_progress)
    client.on_driver_data(init_drivers)
    client.on_race_control_update(on_race_control_update)
    client.on_timing_datum(on_timing_data)
    client.on_driver_status_update(on_driver_status_update)
    client.on_session_status(on_session_status)
    client.on_stint_change(on_stint_change)
    client.on_track_status(lambda s: print(f"{Color.GREEN}Track is {s.message} ({s.id}){Color.OFF}"))
    client.on_clock(lambda c: print(f"{Color.GREEN}Race time is {c.remaining}{Color.OFF}"))
    client.on_session_config(on_session_config)

    timing_tower = TimingTower(client)

    try:
        asyncio.run(client.go())
    except Cancel:
        ...
        
    print(f"Segment statuses: {segment_statuses}")
    print(f"Driver statuses: {driver_statuses_quick}")
    for driver in sorted(timing_tower.drivers.values(), key=lambda d: d.position):
        print(f"{driver.position}: {drivers[driver.driver_number]}")

def on_session_status(status: SessionStatus):
    print(f"{Color.GREEN}Session is {status.status}{Color.OFF}")
        
def on_session_config(config: SessionConfig):
    global track_layout

    print(f"{Color.GREEN}Track config:")
    track_layout = config.layout
    for i in config.layout:
        print(f"{Color.GREEN}\tSector {i}: {config.layout[i]} segments{Color.OFF}")

def on_session_change(session: SessionChange) -> None:
    print(f"{Color.YELLOW}Now watching {session.name}: {session.part} ({session.status}){Color.OFF}")

def on_session_progress(progress: SessionProgress) -> None:
    if isinstance(progress, QualifyingSessionProgress):
        print(f"{Color.GREEN}Qualifying session Q{progress.part}{Color.OFF}")
        return
    
    global lap
    lap = progress.lap
    print(f"{Color.GREEN}Lap {lap}{Color.OFF}")
    
    if args.to > 0 and lap >= args.to:
        raise Cancel()

def on_race_control_update(updates: List[RaceControlMessage]) -> None:
    messages = ", ".join([x.message for x in updates])
    print(f"{Color.RED}Race control: {messages}{Color.OFF}")

    # bug: this gets fired between qualifying sessions too
    # if messages == "CHEQUERED FLAG": # usually fired by itself
    #     raise Cancel()

def init_drivers(data: List[Driver]):
    # don't wipe out the existing data if the websocket reconnects
    # mid-session and re-fires the initial subscription data
    if len(drivers) > 0:
        return
    
    for driver in data:
        drivers[driver.number] = DriverSummary(driver.number, driver.broadcast_name, 0, 99, (1, 1))

@driver_filter
def on_timing_data(data: TimingDatum) -> None:
    if isinstance(data, LapTimingDatum):
        lap_time: LapTimingDatum = data
        if lap_time.overall_fastest:
            print(f"{Color.MAGENTA}\t{drivers[lap_time.driver_id]} set fastest lap: {lap_time.time}{Color.OFF}")
    elif isinstance(data, SegmentTimingDatum):
        segment: SegmentTimingDatum = data
        # print(f"\t{drivers[segment.driver_id]}: {segment.sector_id}:{segment.segment_id} -> {segment.status}")
        last_location = drivers[segment.driver_id].location
        if segment.sector_id == 1 and segment.segment_id == 1:
            drivers[segment.driver_id].location = (1, 1)
        elif last_location[0] < segment.sector_id or last_location[1] < segment.segment_id:
            drivers[segment.driver_id].location = (segment.sector_id, segment.segment_id)

        if segment.status not in segment_statuses:
            segment_statuses[segment.status] = f"{drivers[segment.driver_id]} at {lap}:{segment.sector_id}:{segment.segment_id}"

    elif isinstance(data, SectorTimingDatum):
        sector: SectorTimingDatum = data
        if sector.overall_fastest:
            print(f"{Color.MAGENTA}\t{drivers[data.driver_id]} overall fastest sector {sector.sector_id} ({sector.time}){Color.OFF}")

@driver_filter
def on_driver_status_update(update: DriverStatusUpdate):
    if update.retired:
        print(f"{Color.MAGENTA}\t{drivers[update.driver_id]} retired!{Color.OFF}")
    elif update.stopped:
        print(f"{Color.MAGENTA}\t{drivers[update.driver_id]} stopped{f" in sector {update.sector_id}" if update.sector_id is not None else ""}{Color.OFF}")

    if update.status is None:
        return

    if update.driver_id not in driver_statuses:
        print(f"{Color.CYAN}\t{drivers[update.driver_id]} is now {update.status}{Color.OFF}")
    elif driver_statuses[update.driver_id] != update.status:
        print(f"{Color.CYAN}\t{drivers[update.driver_id]} is now {update.status} (was {driver_statuses[update.driver_id]}){Color.OFF}")

        # these will be in reverse order from their printed binary representation
        # but referring to them by their list index is correct
        old = [(driver_statuses[update.driver_id] >> i) & 1 for i in range(0, 14)]
        new = [(update.status >> i) & 1 for i in range(0, 14)]
        for (i, (old_bit, new_bit)) in enumerate([(old[i], new[i]) for i in range(0, 14)]):
            status = pow(2, i)
            if old_bit and not new_bit:
                print(f"{Color.CYAN}\t{drivers[update.driver_id]} lost status {status}{Color.OFF}")
                # the final summary will show revoked statuses separately as negative, so it's easier
                # to see when they lost a gained status
                status = -status
            elif not old_bit and new_bit:
                print(f"{Color.CYAN}\t{drivers[update.driver_id]} gained status {status}{Color.OFF}")
            else:
                continue
            
            if status not in driver_statuses_quick:
                driver_statuses_quick[status] = f"{drivers[update.driver_id]} at {lap}:{update.sector_id}"
    
    driver_statuses[update.driver_id] = update.status

@driver_filter
def on_stint_change(stint: StintChange):
    if stint.driver_id not in drivers:
        # idk that this is necessary anymore
        print(f"Stint data for unknown driver {stint.driver_id}")
        return

    if stint.stint_number > drivers[stint.driver_id].max_stint:
        print(f"{Color.BLUE}{drivers[stint.driver_id]} started stint {stint.stint_number} on {stint.compound} tyres{Color.OFF}")
        drivers[stint.driver_id].max_stint = stint.stint_number
    else:
        print(f"{Color.BLUE}Correction: stint {stint.stint_number} for {drivers[stint.driver_id]} is on {stint.compound} tyres{Color.OFF}")

if __name__ == "__main__":
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", default="-")
    parser.add_argument("-f", "--from", default=0)
    parser.add_argument("-t", "--to", default=0, type=int)
    parser.add_argument("-d", "--driver", type=int)
    args = parser.parse_args()

    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        ...
