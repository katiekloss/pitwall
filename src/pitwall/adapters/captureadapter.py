import sys
import orjson
from pitwall.adapters.abstract import EOS, PitWallAdapter, Update

class CaptureAdapter(PitWallAdapter):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename

    async def run(self) -> None:
        if self.filename == "-":
            in_file = sys.stdin
        else:
            in_file = open(self.filename, "r")

        for line in in_file:
            try:
                self._message(self.parse_line(line))
            except EOS:
                break
            except:
                print(line) # TODO: remove this
                raise

    def parse_line(self, line: str) -> Update:
        line = line.rstrip()
        if len(line) == 0:
            print("EOF")
            raise EOS()

        (ts, src, data) = line.split(":", 2)
        ts = int(ts)
        data = orjson.loads(data)
        return Update(src, data, ts)