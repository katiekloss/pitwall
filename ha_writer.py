import asyncio
import os

from homeassistant_api import Client as HomeAssistantClient, State
from pitwall.events import SessionStatus
from pitwall.adapters import CaptureAdapter
from pitwall import PitWallClient
from pitwall.events.session import SessionProgress
from pitwall.util.timing_tower import TimingLine, TimingTower

ha: HomeAssistantClient = None
session_status: SessionStatus = None

async def main():
    global ha
    client = PitWallClient(CaptureAdapter("-"))
    client.on_session_status(on_session_status)
    client.on_session_progress(on_session_progress)

    timing = TimingTower(client)
    timing.on_position_change(on_position_change)

    with HomeAssistantClient(os.environ["HOMEASSISTANT_URL"], os.environ["HOMEASSISTANT_TOKEN"]) as ha:
        await client.go()

def on_session_status(update: SessionStatus):
    global session_status
    session_status = update
    ha.set_state(State(entity_id="sensor.f1_session", state=update.status))

def on_session_progress(update: SessionProgress):
    ha.set_state(State(entity_id="sensor.f1_session", state=session_status.status if session_status else "Unknown", attributes={"lap": update.lap}))

def on_position_change(driver: TimingLine):
    if driver.position == 1:
        ha.set_state(State(entity_id="sensor.f1_leader", state=driver.name, attributes={"number": driver.driver_number}))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass