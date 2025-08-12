import pytest

from pitwall import PitWallClient
from pitwall.adapters import CaptureAdapter
from pitwall.events import SessionConfig

@pytest.mark.asyncio
class TestSessionResults:
    session_config: SessionConfig | None = None

    async def test_hungary_2025(self):
        client = PitWallClient(CaptureAdapter("data/2025_hungary_race.txt"))
        client.on_session_config(self.on_session_config)

        await client.go()
        
        assert self.session_config is not None
        assert len(self.session_config.layout) == 3
        assert self.session_config.layout[1] == 7
        assert self.session_config.layout[2] == 8
        assert self.session_config.layout[3] == 6
    
    def on_session_config(self, config):
        self.session_config = config