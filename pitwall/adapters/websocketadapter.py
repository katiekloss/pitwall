import asyncio

from pitwall.adapters.abstract import PitWallAdapter

class WebsocketAdapter(PitWallAdapter):
    def __init__(self, websocketclient):
        self.client = websocketclient
        self.client.on("feed", self.on_feed)

    async def on_feed(self, message):
        source = message[0]
        data = message[1]
        print(f'{source}: {data}')

    async def on_subscribe(self, message):
        print('subscribed')

    async def start(self):
        await asyncio.gather(
            self.client.run(),
            self.client.send("Subscribe", [["SessionInfo", "Heartbeat", "DriverList", "ExtrapolatedClock", "RaceControlMessages", "SessionStatus", "TeamRadio", "TimingAppData", "TimingStats", "TrackStatus", "WeatherData", "Position.z", "CarData.z", "SessionData", "TimingData"]], self.on_subscribe))

