import pytest

from pitwall import PitWallClient
from pitwall.adapters import CaptureAdapter
from pitwall.events import SessionConfig
from pitwall.util import TimingTower

@pytest.mark.asyncio
class TestSessionResults:
    session_config: SessionConfig | None = None

    async def test_hungary_race(self):
        client = PitWallClient(CaptureAdapter("data/2025_hungary_race.txt"))
        client.on_session_config(self.on_session_config)
        timing = TimingTower(client)

        await client.go()
        
        assert self.session_config is not None
        assert len(self.session_config.layout) == 3
        assert self.session_config.layout[1] == 7
        assert self.session_config.layout[2] == 8
        assert self.session_config.layout[3] == 6

        results = [d.driver_number for d in sorted(timing.drivers.values(), key=lambda d: d.position)]
        assert results == [4, 81, 63, 16, 14, 5, 18, 30, 1, 12, 6, 44, 27, 55, 23, 31, 22, 43, 10, 87]
    
    def on_session_config(self, config):
        self.session_config = config