#!/usr/bin/env python

import copy
import queue
import sys
from anyio import run
import asyncio
import os
import time
import argparse
import logging

import orjson
from pitwall.adapters.abstract import EOS, PitWallAdapter, Update
from pitwall.adapters.captureadapter import CaptureAdapter

class RealtimeReplayAdapter(PitWallAdapter):
    _inner_adapter: PitWallAdapter
    _multiplier: int
    _log: logging.Logger
    _queue: asyncio.Queue

    def __init__(self, inner_adapter: PitWallAdapter, multiplier = 1):
        super().__init__()
        self._inner_adapter = inner_adapter
        self._inner_adapter.on_message(self._on_message)
        self._multiplier = multiplier
        self._log = logging.getLogger(__name__)
        self._queue = asyncio.Queue()

    def _on_message(self, update: Update):
        self._queue.put_nowait(update)

    async def run(self):
        await asyncio.gather(self._inner_adapter.run(),
                             self._inner_run())
        
    async def _inner_run(self):
        last_ts = None

        while True:
            next_update: Update = await self._queue.get()

            if last_ts is None: # or if we spent any amount of time waiting on the queue (i.e. it's already realtime)
                ...
            else:
                wait_s = (next_update.ts - last_ts) / 1000000000
                # helps get through waiting forever
                if wait_s > 5:
                    wait_s = 5
                wait_s = wait_s / self._multiplier
                self._log.debug("Need to wait %.3fs for next update", wait_s)
                await asyncio.sleep(wait_s)

            # measure the amount of time spent processing the message callbacks
            # and add it to the current update's timestamp, so that the next
            # computed wait period is that much shorter. This only really matters
            # if the inner adapter always has data available, like a replay from
            # a captured event; otherwise, we'll spend more time waiting for
            # the next message.
            offset_time = time.time_ns()

            # also, some other adapters do shenanigans with the message timestamps,
            # so fire a copy to avoid them breaking our timing calculations
            self._message(copy.copy(next_update))
            
            offset_time = time.time_ns() - offset_time
            if offset_time < 0:
                offset_time = 0
            last_ts = next_update.ts + offset_time

async def main():
    if args.output is not None:
        if os.path.exists(args.output):
            os.remove(args.output)

        os.mkfifo(args.output)
        output = open(args.output, "a")
    else:
        output = sys.stdout

    adapter = RealtimeReplayAdapter(CaptureAdapter(args.input), args.multiplier)
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
    except (KeyboardInterrupt,BrokenPipeError,EOS):
        ...
    finally:
        try:
            if args.output is not None:
                os.remove(args.output)
        except (NameError,FileNotFoundError):
            ...
