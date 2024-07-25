#!env/bin/python
import sys
import asyncio
import orjson
import time

from pysignalr.client import SignalRClient

async def on_open():
    ...

async def on_close():
    ...

async def on_error(x):
    print(f"error: {x}")

async def on_feed(update):
    now = time.time_ns()
    source = update[0]
    data = orjson.dumps(update[1]).decode('utf-8')
    print(f'{now}:{source}:{data}')

async def on_subscribe(snapshot):
    now = time.time_ns()
    snapshot = orjson.dumps(snapshot.result).decode('utf-8')
    print(f"{now}:init:{snapshot}")

async def main():
    timing_client = SignalRClient("wss://livetiming.formula1.com/signalrcore")

    timing_client.on_open(on_open)
    timing_client.on_close(on_close)
    timing_client.on_error(on_error)
    timing_client.on("feed", on_feed)

    await asyncio.gather(
        timing_client.run(),
        timing_client.send("Subscribe", [["SessionInfo", "Heartbeat", "DriverList", "ExtrapolatedClock", "RaceControlMessages", "SessionStatus", "TeamRadio", "TimingAppData", "TimingStats", "TrackStatus", "WeatherData", "Position.z", "CarData.z", "SessionData", "TimingData"]], on_subscribe))

asyncio.run(main())

