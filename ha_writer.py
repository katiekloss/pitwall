import asyncio
import os

from homeassistant_api import Client as HomeAssistantClient, State
from pitwall.events import SessionStatus
from pitwall.adapters import CaptureAdapter
from pitwall import PitWallClient

ha: HomeAssistantClient

async def main():
    global ha
    client = PitWallClient(CaptureAdapter("-"))
    client.on_session_status(on_session_status)

    with HomeAssistantClient(os.environ["HOMEASSISTANT_URL"], os.environ["HOMEASSISTANT_TOKEN"]) as ha:
        await client.go()

def on_session_status(update: SessionStatus):
    ha.set_state(State(entity_id="sensor.f1_session", state=update.status))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass