#!/usr/bin/env python
import sys
import argparse
import orjson
import time
import os

drivers = dict()
statuses = dict()
locations = dict()
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
    if len(line) == 0 or lap > 2:
        print(f"EOF")
        raise Cancel()

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
    elif src == "SessionStatus":
        status = data["Status"]
        print(f"Session is {status}")
    elif src == "SessionData":
        if "Series" not in data or isinstance(data["Series"], list):
            return

        session = data["Series"][list(data["Series"].keys())[0]]
        if "Lap" in session:
            lap = int(data["Series"][list(data["Series"].keys())[0]]["Lap"])
            print(f"Lap {lap}")
        elif "QualifyingPart" in session:
            print(f"Qualifying session, no lap count")
        else:
            raise KeyError("Unknown SessionData format")

    elif src == "TimingData":
        for driver_id in data["Lines"].keys():
            if driver_id != "81":
                continue
            driver = data["Lines"][driver_id]
            print(f"{ts}: {driver}")
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
                sector_id = int(sector_id)
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

                for segment_id in sector["Segments"].keys(): # order these?
                    segment = sector["Segments"][segment_id]
                    segment_id = int(segment_id)
                    status = segment["Status"]

                    if status > 0 and status != 2052:
                        if driver_id in locations:
                            last_location = locations[driver_id]
                            if sector_id == 0 and segment_id <= 1:
                                print("Lap!") # should actually happen at the end of the max segment, but we don't know what that is yet
                                locations[driver_id] = (0, 0)
                            elif last_location[0] < sector_id or last_location[1] < segment_id:
                                print(f"Finished segment {sector_id}:{segment_id}")
                                locations[driver_id] = (sector_id, segment_id)
                        else:
                            locations[driver_id] = (sector_id, segment_id)

                    if status not in statuses:
                        statuses[status] = f"{drivers[driver_id]} at {lap}:{sector_id}:{segment_id}"
    elif src == "TimingAppData" or src == "TimingStats":
        for driver_id in data["Lines"].keys():
            if driver_id != "81" or driver_id not in drivers:
                continue
            print(data["Lines"][driver_id])
    elif src == "TrackStatus":
        message = data["Message"]
        status = data["Status"]
        print(f"Track is {message} ({status})")
    elif src == "ExtrapolatedClock":
        t = data["Remaining"]
        print(f"Race time is {t}")
    elif src in ["Heartbeat", "WeatherData", "TeamRadio"]:
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
