import asyncio
from dataclasses import dataclass
import os

import homeassistant_api
from homeassistant_api import State
from homeassistant_api.rawclient import RawClient as HomeAssistantClient

from pitwall import PitWallClient
from pitwall.adapters import CaptureAdapter
from pitwall.events import SessionStatus, LapSessionProgress, QualifyingSessionProgress, SessionChange, SessionProgress
from pitwall.util.timing_tower import TimingLine, TimingTower

@dataclass
class SessionState:
    status: str
    lap: int
    q: int

ha: HomeAssistantClient = None # ty: ignore[invalid-assignment]
session: SessionState = SessionState(None, 0, 0)

async def main():
    global ha
    client = PitWallClient(CaptureAdapter("-"))
    client.on_session_status(on_session_status)
    client.on_session_progress(on_session_progress)
    client.on_session_change(on_session_change)

    timing = TimingTower(client)
    timing.on_position_change(on_position_change)

    with homeassistant_api.Client(os.environ["HOMEASSISTANT_URL"], os.environ["HOMEASSISTANT_TOKEN"]) as ha:
        await client.go()

def on_session_change(update: SessionChange):
    if update.status == "Generating":
        ha.set_state(State(entity_id="calendar.f1", state="On"))
    elif update.status == "Complete":
        ha.set_state(State(entity_id="calendar.f1", state="Off"))

def on_session_status(update: SessionStatus):
    session.status = update.status
    update_session()

def on_session_progress(update: SessionProgress):
    if isinstance(update, LapSessionProgress):
        session.lap = update.lap
    elif isinstance(update, QualifyingSessionProgress):
        session.q = update.part

    update_session()

def on_position_change(driver: TimingLine):
    if driver.position == 1:
        ha.set_state(State(entity_id="sensor.f1_leader", state=driver.name, attributes={"number": driver.driver_number}))

def update_session():
    if session.lap > 0:
        progress = f"Lap {session.lap}"
    elif session.q > 0:
        progress = f"Q{session.q}"

    status = session.status if session.status is not None else "Unknown"

    ha.set_state(State(entity_id="sensor.f1_session", state=status, attributes={"progress": progress}))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass