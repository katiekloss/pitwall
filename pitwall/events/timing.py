from dataclasses import dataclass

@dataclass
class TimingDatum:
    driver_id: int

@dataclass
class SegmentTimingDatum(TimingDatum):
    sector_id: int
    segment_id: int
    status: int
    """
    Driver's status flags in the segment. Some (guesses at) values:
    - 2048: Complete
    - 2049: Personal best + complete
    - 2050: Unknown
    - 2051: Overall best
    - 2052: Crashed/stopped
    - 2064: Safety car?
    """

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
    sector_id: int | None
    retired: bool | None
    stopped: bool | None
    status: int | None

@dataclass
class DriverPositionUpdate(TimingDatum):
    position: int

@dataclass
class StintChange:
    driver_id: int
    stint_number: int
    compound: str