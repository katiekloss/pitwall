import asyncio
import queue
import pika
import logging
import orjson
import os
import sys

from replay import RealtimeReplayAdapter
# from pitwall.adapters import WebsocketAdapter
# from pysignalr.client import SignalRClient
from pika.adapters.blocking_connection import BlockingChannel
from pika.exchange_type import ExchangeType

channel: BlockingChannel
updates: queue.Queue = queue.Queue()

logging.basicConfig(
    format="%(asctime)s %(name)s: %(message)s",
    level=logging.DEBUG,
)

async def main():
    global channel

    rabbit = pika.BlockingConnection(pika.URLParameters(os.environ["RABBITMQ_URL"]))
    channel = rabbit.channel()
    channel.exchange_declare("pitwall", exchange_type=ExchangeType.topic)

    #adapter = WebsocketAdapter(SignalRClient("wss://livetiming.formula1.com/signalrcore"))
    adapter = RealtimeReplayAdapter(sys.argv[1])
    adapter.on_message(lambda u: channel.basic_publish(exchange='pitwall', routing_key=u.src, body=orjson.dumps(u.data)))

    await adapter.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
        ...