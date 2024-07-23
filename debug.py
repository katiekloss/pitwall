#!env/bin/python

import asyncio
import sys

from pitwall.client import PitWallClient
from pitwall.adapters.websocketadapter import WebsocketAdapter
from pitwall.adapters.captureadapter import CaptureAdapter
from pysignalr.client import SignalRClient

async def main():
    if sys.argv[1] == "--live":
        adapter = WebsocketAdapter(SignalRClient("wss://livetiming.formula1.com/signalrcore"))
    elif sys.argv[1] == "--capture":
        adapter = CaptureAdapter(sys.argv[2])

    client = PitWallClient(adapter)
    await client.start()

if __name__ == "__main__":
    asyncio.run(main())

