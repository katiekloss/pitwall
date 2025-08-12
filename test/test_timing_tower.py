from typing import List
import pytest

from pitwall import PitWallClient
from pitwall.adapters import CaptureAdapter
from pitwall.util import TimingTower

@pytest.mark.asyncio
class TestTimingTower:
    async def assert_session_results(self, filename: str, results: List[int], dnf: List[int]=[]):
        client = PitWallClient(CaptureAdapter(filename))
        timing = TimingTower(client)

        await client.go()
        
        assert [d.driver_number for d in timing.results[:len(results)]] == results

        if len(dnf) == 0:
            assert len(timing.results) == len(results)
        else:
            # assert the DNFs but not their order
            assert sorted([d.driver_number for d in timing.results[-len(dnf):]]) == sorted(dnf)

    async def test_hungary_2025(self):
         await self.assert_session_results("data/2025_hungary_race.txt",
                                           [4, 81, 63, 16, 14, 5, 18, 30, 1, 12, 6, 44, 27, 55, 23, 31, 22, 43, 10],
                                           dnf=[87])
    
    async def test_brazil_2024_sprint(self):
        # Max caught a penalty so Leclerc took third after the race
        await self.assert_session_results("data/2024_brazil_sprint.txt",
                                          [4, 81, 1, 16, 55, 63, 10, 11, 30, 23, 44, 43, 31, 50, 22, 77, 24, 14, 18],
                                          dnf=[27])
        
    async def test_brazil_2024_gp(self):
        await self.assert_session_results("data/2024_brazil_race.txt",
                                          [1, 31, 10, 63, 16, 4, 22, 81, 30, 44, 11, 50, 77, 14, 24],
                                          dnf=[55, 43, 23, 18, 27])
        
    async def test_belgium_2024(self):
        # George was DSQed after the race for weight
        await self.assert_session_results("data/2024_belgium_gp_race.txt",
                                          [63, 44, 81, 16, 1, 4, 55, 11, 14, 31, 3, 18, 23, 10, 20, 77, 22, 2, 27],
                                          dnf=[24])
    
    async def test_dutch_2024(self):
        await self.assert_session_results("data/2024_dutch_gp_race.txt",
                                           [4, 1, 16, 81, 55, 11, 63, 44, 10, 14, 27, 3, 18, 23, 31, 2, 22, 20, 77, 24])
    
    async def test_qatar_2024(self):
        await self.assert_session_results("data/2024_qatar_gp_race.txt",
                                          [1, 16, 81, 63, 10, 55, 14, 24, 20, 4, 77, 44, 22, 30, 23, 27],
                                          dnf=[27, 11, 18, 31, 43])