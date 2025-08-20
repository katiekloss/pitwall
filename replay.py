#!/usr/bin/env python

import sys
from anyio import run
import asyncio
import os
import time
import argparse
import logging

import orjson
from pitwall.adapters.abstract import PitWallAdapter, Update

class RealtimeReplayAdapter(PitWallAdapter):
    _filename: str
    _multiplier: int
    _log: logging.Logger

    def __init__(self, filename, multiplier = 1):
        super().__init__()
        self._filename = filename
        self._multiplier = multiplier
        self._log = logging.getLogger(__name__)

    async def run(self):
        with open(self._filename) as file:
            last_ts = None
            for next_line in file:
                (ts, type, data) = next_line.split(":", 2)
                ts = int(ts)
                data = orjson.loads(data.rstrip())
                if last_ts is None:
                    ...
                else:
                    wait_s = (ts - last_ts) / 1000000000
                    # helps get through waiting forever
                    if wait_s > 5:
                        wait_s = 5
                    wait_s = wait_s / self._multiplier
                    self._log.debug("Need to wait %.3fs for next update", wait_s)
                    await asyncio.sleep(wait_s)

                offset_time = time.time_ns()
                self._message(Update(type, data, ts))
                offset_time = time.time_ns() - offset_time
                if offset_time < 0:
                    offset_time = 0
                last_ts = ts + offset_time

async def main():
    if args.output is not None:
        if os.path.exists(args.output):
            os.remove(args.output)

        os.mkfifo(args.output)
        output = open(args.output, "a")
    else:
        output = sys.stdout

    adapter = RealtimeReplayAdapter(args.input, args.multiplier)
    adapter.on_message(lambda u: output.write(f"{u.ts}:{u.src}:{orjson.dumps(u.data).decode()}\n"))
    await adapter.run()

if __name__ == "__main__":
    try:
        global args
        parser = argparse.ArgumentParser()
        parser.add_argument("-i", "--input", required=True)
        parser.add_argument("-o", "--output")
        parser.add_argument("-x", "--multiplier")
        args = parser.parse_args()
        if args.multiplier is not None:
            args.multiplier = int(args.multiplier)
        else:
            args.multiplier = 1

        run(main)
    except (KeyboardInterrupt,BrokenPipeError):
        ...
    finally:
        try:
            if args.output is not None:
                os.remove(args.output)
        except (NameError,FileNotFoundError):
            ...
