#!/usr/bin/env python
import sys
import asyncio
import orjson
import time
import argparse

from pysignalr.client import SignalRClient

last_update = time.time()

class Cancel(Exception):
    ...

async def on_open():
    ...

async def on_close():
    ...

async def on_error(x):
    print(f"error: {x}")

async def on_feed(update):
    global last_update
    last_update = time.time()

    now = time.time_ns()
    source = update[0]
    data = orjson.dumps(update[1]).decode('utf-8')
    write(f'{now}:{source}:{data}')

    if source == "SessionStatus" and update[1]["Status"] == "Finalised":
        raise Cancel()

async def on_subscribe(snapshot):
    now = time.time_ns()
    snapshot = orjson.dumps(snapshot.result).decode('utf-8')
    write(f"{now}:init:{snapshot}")

    print("Subscribed")

async def timeout():
    while True:
        await asyncio.sleep(5 * 60)
        if time.time() - last_update > 5 * 60:
            print("5 minutes since last update, done!")
            raise Cancel()

def write(line):
    out_file.write(line)
    out_file.flush()

async def main():
    timing_client = SignalRClient("wss://livetiming.formula1.com/signalrcore")

    timing_client.on_open(on_open)
    timing_client.on_close(on_close)
    timing_client.on_error(on_error)
    timing_client.on("feed", on_feed)

    await asyncio.gather(
        timeout(),
        timing_client.run(),
        timing_client.send("Subscribe", [["SessionInfo", "Heartbeat", "DriverList", "ExtrapolatedClock", "RaceControlMessages", "SessionStatus", "TeamRadio", "TimingAppData", "TimingStats", "TrackStatus", "WeatherData", "Position.z", "CarData.z", "SessionData", "TimingData"]], on_subscribe))

if __name__ == "__main__":
    global args
    global out_file

    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()

    out_file = open(args.output, "a")

    try:
        asyncio.run(main())
    except Cancel:
        ...
    except KeyboardInterrupt:
        ...
    finally:
        out_file.close()
