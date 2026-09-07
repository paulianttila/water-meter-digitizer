"""Lightweight Python MQTT broker runner using amqtt for integration tests."""

import asyncio
import logging
from amqtt.broker import Broker

logger = logging.getLogger("mqtt_broker")

config = {
    "listeners": {
        "default": {
            "type": "tcp",
            "bind": "127.0.0.1:1883",
        }
    },
    "auth": {
        "allow-anonymous": True,
    },
}


async def run_broker():
    broker = Broker(config)
    await broker.start()
    try:
        while True:
            await asyncio.sleep(1)
    except (asyncio.CancelledError, KeyboardInterrupt):
        await broker.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(run_broker())
    except KeyboardInterrupt:
        pass
