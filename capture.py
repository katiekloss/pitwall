#!/usr/bin/env python
import asyncio
import logging
import orjson
import time
import argparse
import os

from pysignalr.client import SignalRClient

logging.basicConfig(
    format="%(asctime)s %(name)s: %(message)s",
    level=logging.INFO,
)

last_update = time.time()
out_file = None
current_session_key = None

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
    global out_file
    global current_session_key

    last_update = time.time()

    now = time.time_ns()
    source = update[0]
    data = orjson.dumps(update[1]).decode('utf-8')

    if source == "SessionInfo" and args.continuous:
        if update[1]["Key"] != current_session_key:
            current_session_key = update[1]["Key"]
            print("Switching to " + update[1]["Meeting"]["Name"] + " " + update[1]["Name"])

            if out_file is not None:
                out_file.close()
            out_file = open(os.path.join(args.output, update[1]["Meeting"]["Name"] + " - " + update[1]["Name"] + ".txt"), "a")

    write(f'{now}:{source}:{data}')

    if source == "SessionStatus" and update[1]["Status"] == "Finalised":
        if args.continuous:
            print("Session complete")
            out_file.close() # ty: ignore[possibly-unbound-attribute]
            out_file = None
        else:
            raise Cancel()

async def on_subscribe(snapshot):
    global out_file
    global current_session_key

    now = time.time_ns()

    print("Capturing " + snapshot.result["SessionInfo"]["Meeting"]["Name"] + " " + snapshot.result["SessionInfo"]["Name"])
    if snapshot.result["SessionStatus"]["Status"] in ("Complete", "Finalised", "Ends"):
        print("Session is finished")
        if not args.continuous:
            raise Cancel()
        else:
            return

    if args.continuous and out_file is None:
        current_session_key = snapshot.result["SessionInfo"]["Key"]
        out_file = open(os.path.join(args.output, snapshot.result["SessionInfo"]["Meeting"]["Name"] + " - " + snapshot.result["SessionInfo"]["Name"] + ".txt"), "a")

    snapshot = orjson.dumps(snapshot.result).decode('utf-8')
    write(f"{now}:init:{snapshot}")

    print("Subscribed")

async def timeout():
    while not args.continuous:
        await asyncio.sleep(5 * 60)
        if time.time() - last_update > 5 * 60:
            print("5 minutes since last update, done!")
            raise Cancel()

def write(line):
    if out_file is None:
        return

    out_file.write(line + '\n')
    out_file.flush()

async def main():
    timing_client = SignalRClient("wss://livetiming.formula1.com/signalrcore", connection_timeout=30)
    timing_client._transport._skip_negotiation = True
    
    timing_client.on_open(on_open)
    timing_client.on_close(on_close)
    timing_client.on_error(on_error)
    timing_client.on("feed", on_feed)

    await asyncio.gather(
        timing_client.run(),
        timing_client.send("Subscribe", [["SessionInfo", "Heartbeat", "DriverList", "ExtrapolatedClock", "RaceControlMessages", "SessionStatus", "TeamRadio", "TimingAppData", "TimingStats", "TrackStatus", "WeatherData", "Position.z", "CarData.z", "SessionData", "TimingData"]], on_subscribe),
        timeout())

if __name__ == "__main__":
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("-c", "--continuous", action="store_true")
    args = parser.parse_args()

    if not args.continuous:
        out_file = open(args.output, "a")

    try:
        asyncio.run(main())
    except Cancel:
        ...
    except KeyboardInterrupt:
        ...
    finally:
        if out_file is not None:
            out_file.close()
