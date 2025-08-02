from dataclasses import dataclass

@dataclass
class TimingDatum:
    driver_id: int

@dataclass
class SegmentTimingDatum(TimingDatum):
    sector_id: int
    segment_id: int
    status: int

@dataclass
class SectorTimingDatum(TimingDatum):
    sector_id: int
    personal_fastest: bool
    overall_fastest: bool
    """Set if the driver currently holds the sector's fastest time (even if it was achieved on a previous lap)"""
    time: float

@dataclass
class LapTimingDatum(TimingDatum):
    lap_number: int
    personal_fastest: bool
    overall_fastest: bool
    time: float

@dataclass
class DriverStatusUpdate(TimingDatum):
    sector_id: int
    stopped: bool

@dataclass
class StintChange:
    driver_id: int
    stint_number: int
    compound: str