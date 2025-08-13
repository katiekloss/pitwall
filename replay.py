#!/usr/bin/env python

import sys
from anyio import open_file, run
import asyncio
import os
import time
import argparse

async def main():
    if args.output is not None:
        if os.path.exists(args.output):
            os.remove(args.output)

        os.mkfifo(args.output)
        output = open(args.output, "a")
    else:
        output = sys.stdout

    async with await open_file(args.input) as file:
        last_ts = None
        async for next_line in file:
            (ts, type, data) = next_line.split(":", 2)
            ts = int(ts)
            data = data.rstrip()
            if last_ts is None:
                ...
            else:
                wait_s = (ts - last_ts) / 1000000000
                # helps get through waiting forever
                if wait_s > 5:
                    wait_s = 5
                wait_s = wait_s / args.multiplier
                await asyncio.sleep(wait_s)

            offset_time = time.time_ns()
            output.write(f"{ts}:{type}:{data}\n")
            output.flush()
            offset_time = time.time_ns() - offset_time
            if offset_time < 0:
                offset_time = 0
            last_ts = ts + offset_time

    if output is not None:
        output.close()

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
        os.remove(args.output)
    except (NameError,FileNotFoundError):
        ...
