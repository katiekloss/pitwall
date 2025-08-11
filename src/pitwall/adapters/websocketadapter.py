import asyncio
import time

import pysignalr.client

from pitwall.adapters.abstract import PitWallAdapter, Update

class WebsocketAdapter(PitWallAdapter):
    client: pysignalr.client.SignalRClient

    def __init__(self, websocketclient : pysignalr.client.SignalRClient):
        super().__init__()
        self.client = websocketclient
        self.client.on("feed", self.on_feed)

    async def on_feed(self, message):
        source = message[0]
        data = message[1]
        self._message(Update(source, data, time.time_ns()))

    async def on_subscribe(self, message):
        self._message(Update("init", message.result, time.time_ns()))

    async def run(self) -> None:
        await asyncio.gather(
            self.client.send("Subscribe",
                             [["SessionInfo", "Heartbeat", "DriverList", "ExtrapolatedClock", "RaceControlMessages", "SessionStatus", "TeamRadio", "TimingAppData", "TimingStats", "TrackStatus", "WeatherData", "Position.z", "CarData.z", "SessionData", "TimingData"]],
                             self.on_subscribe),
            self.client.run())