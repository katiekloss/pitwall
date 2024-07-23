from pitwall.adapters.abstract import PitWallAdapter

class CaptureAdapter(PitWallAdapter):
    def __init__(self, filename):
        self.filename = filename

    async def start(self):
        pass

