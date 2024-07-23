from pitwall.adapters.abstract import PitWallAdapter

class PitWallClient:
    def __init__(self, adapter):
        self.adapter = adapter

    async def start(self):
        await self.adapter.start()

    async def stop(self):
        await self.adapter.stop()

