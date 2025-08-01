from dataclasses import dataclass

@dataclass
class TimingDatum:
    driver_id: int

@dataclass
class SegmentTimingDatum(TimingDatum):
    sector_id: int
    segment_id: int
    personal_fastest: bool
    time: float

@dataclass
class SectorTimingDatum(TimingDatum):
    sector_id: int
    personal_fastest: bool
    overall_fastest: bool
    time: float

@dataclass
class LapTimingDatum(TimingDatum):
    lap_number: int
    personal_fastest: bool
    overall_fastest: bool
    time: float

@dataclass
class DriverStatusUpdate(TimingDatum):
    stopped: bool