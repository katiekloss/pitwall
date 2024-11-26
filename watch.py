#!/usr/bin/env python
import sys
import argparse
import orjson
import time
import os

drivers = dict()
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

    in_file = open(args.input, "r")
    for line in in_file:
        try:
            on_line(line)
        except Cancel:
            break
        except:
            print(line)
            raise

    print(f"Segment statuses: {statuses}")


def on_line(line):
    global lap

    line = line.rstrip()
    if len(line) == 0:
        print(f"EOF")
        return

    (ts, src, data) = line.split(":", 2)
    ts = int(ts)
    data = orjson.loads(data)

    if src == "init":
        change_session(data["SessionInfo"])
        init_drivers(data["DriverList"])
    elif src == "SessionInfo":
        change_session(data)
    elif src == "DriverList":
        init_drivers(data)
    elif src == "RaceControlMessages":
        if isinstance(data["Messages"], list):
            messages = data["Messages"]
        elif isinstance(data["Messages"], dict):
            messages = list(data["Messages"].values())

        messages = ", ".join([x["Message"] for x in messages])
        print(f"Race control: {messages}")
        if messages == "CHEQUERED FLAG":
            raise Cancel()

    elif src == "SessionData":
        if "Series" not in data or isinstance(data["Series"], list):
            return

        lap = int(data["Series"][list(data["Series"].keys())[0]]["Lap"])
        print(f"Lap {lap}")
    elif src == "TimingData":
        for driver_id in data["Lines"].keys():
            driver = data["Lines"][driver_id]
            if driver_id not in drivers:
                print(f"\t{driver_id}: Unknown")
                continue
            if "Sectors" not in driver:
                # probably "GapToLeader" and/or "IntervalToPositionAhead" instead
                continue

            # happens at the start of the race to reset everyone, for some reason it's not a dict
            if isinstance(driver["Sectors"], list):
                driver["Sectors"] = dict([(i, x) for i, x in enumerate(driver["Sectors"])])

            for sector_id in driver["Sectors"].keys():
                sector = driver["Sectors"][sector_id]
                if "Stopped" in sector:
                    print(f"\t\t{drivers[driver_id]} stopped in sector {sector_id}")
                    continue
                elif "Value" in sector:
                    if sector["Value"] != "":
                        sector_time = float(sector["Value"])
                    else:
                        ... # probably clearing the last n-1 sectors at the start of a new lap
                    continue
                elif "PreviousValue" in sector:
                    continue

                if "PersonalFastest" in sector:
                    print(f"Personal fastest sector {sector_id}: {drivers[driver_id]}")
                    continue
                elif "OverallFastest" in sector:
                    print(f"Overall fastest sector {sector_id}: {drivers[driver_id]}")
                    continue
                elif "Segments" not in sector:
                    print(f"\t{sector}")
                    # "Value" str int "OverallFastest" bool and "PersonalFastest" bool
                    continue
                elif isinstance(sector["Segments"], list): # same as the above one for driver[Sectors]
                    sector["Segments"] = dict([(i, x) for i, x in enumerate(sector["Segments"])])

                for segment_id in sector["Segments"].keys():
                    segment = sector["Segments"][segment_id]
                    status = segment["Status"]
                    if status not in statuses:
                        statuses[status] = f"{drivers[driver_id]} at {lap}:{sector_id}:{segment_id}"
    elif src == "TrackStatus":
        message = data["Message"]
        status = data["Status"]
        print(f"Track is {message} ({status})")
    elif src == "ExtrapolatedClock":
        t = data["Remaining"]
        print(f"Race time is {t}")
    elif src in ["Heartbeat", "TimingStats", "TimingAppData", "WeatherData", "TeamRadio"]:
        ...
    else:
        print(line)

def change_session(data):
    event = data["Meeting"]["Name"]
    session = data["Name"]
    status = data["ArchiveStatus"]["Status"]
    print(f"Now watching {event}: {session} ({status})")

def init_drivers(data):
    if isinstance(data, dict):
        for driver_id in data.keys():
            if driver_id == "_kf":
                break

            if "BroadcastName" not in data[driver_id]:
                continue

            drivers[driver_id] = data[driver_id]["BroadcastName"]
    else:
        for driver in data:
            drivers[str(driver["RacingNumber"])] = driver["BroadcastName"]

if __name__ == "__main__":
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True)
    args = parser.parse_args()

    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        ...
