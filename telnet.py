#!env/bin/python
import sys
import asyncio

from pysignalr.client import SignalRClient

async def on_open():
    print("connected")

async def on_close():
    print("disconnected")

async def on_error(x):
    print(f"error: {x}")

async def on_feed(update):
    source = update[0]
    data = update[1]
    print(f'{source}: {data}')

async def on_subscribe(snapshot):
    print(f'subscribed: {snapshot}')

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

