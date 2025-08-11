from dataclasses import dataclass

type TimingDatum = SegmentTimingDatum | SectorTimingDatum | LapTimingDatum

@dataclass
class SegmentTimingDatum:
    driver_id: int
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
class SectorTimingDatum:
    driver_id: int
    sector_id: int
    personal_fastest: bool
    overall_fastest: bool
    """Set if the driver currently holds the sector's fastest time (even if it was achieved on a previous lap)"""
    time: float

@dataclass
class LapTimingDatum:
    driver_id: int
    lap_number: int
    personal_fastest: bool
    overall_fastest: bool
    time: float

@dataclass
class DriverStatusUpdate:
    driver_id: int
    sector_id: int | None
    retired: bool | None
    stopped: bool | None
    status: int | None
    """
    Driver's overall status flags. Guesses:
    - 512: Incident related ("noted"). Gained and lost immediately.
    - 8192: Incident related ("noted"). Also gained and lost immediately.
    - 32: In pit lane?
    - 4096: Set = pit in, unset = pit out?
    - 16: Pit related
    - 512: Pit related
    - 4: Retired/out
    - 8: Retired/out
    """

@dataclass
class DriverPositionUpdate:
    driver_id: int
    position: int

@dataclass
class StintChange:
    driver_id: int
    stint_number: int
    compound: str