import logging
import sys
import orjson
from anyio import open_file, wrap_file
from pitwall.adapters.abstract import EOS, PitWallAdapter, Update

class CaptureAdapter(PitWallAdapter):

    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self._log = logging.getLogger(__name__)

    async def run(self) -> None:
        self._log.info("Starting")
        if self.filename == "-":
            in_file = wrap_file(sys.stdin)
        else:
            in_file = await open_file(self.filename, "r")

        async with in_file:
            self._log.debug("Opened %s", self.filename)
            async for line in in_file:
                try:
                    await self._message(self.parse_line(line))
                except EOS:
                    self._log.info("End of stream")
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