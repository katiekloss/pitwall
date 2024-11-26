#!/usr/bin/env python
import sys
import argparse
import asyncio

async def main():
    in_file = open(args.input, "r")
    for line in in_file:
        line = line.rstrip()
        print(line, flush=True)

if __name__ == "__main__":
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True)
    args = parser.parse_args()

    try:
        asyncio.run(main())
    except:
        raise
