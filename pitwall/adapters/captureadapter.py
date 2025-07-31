from typing import AsyncIterator
import orjson
from pitwall.adapters.abstract import EOS, PitWallAdapter, Update

class CaptureAdapter(PitWallAdapter):
    def __init__(self, filename):
        self.filename = filename

    async def run(self) -> AsyncIterator[Update]:
        in_file = open(self.filename, "r")
        for line in in_file:
            try:
                yield self.on_line(line)
            except EOS:
                break
            except:
                print(line)
                raise

    def on_line(self, line: str) -> Update:
        line = line.rstrip()
        if len(line) == 0:
            print("EOF")
            raise EOS()

        (ts, src, data) = line.split(":", 2)
        ts = int(ts)
        data = orjson.loads(data)
        return Update(src, data, ts)