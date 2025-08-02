from dataclasses import dataclass
from typing import List

@dataclass
class SessionChange:
    name: str
    part: str
    status: str

@dataclass
class SessionProgress:
    lap: int # not always though

@dataclass
class RaceControlUpdate:
    # bug: not actually a string
    messages: List[str]

@dataclass
class SessionStatus:
    status: str

@dataclass
class TrackStatus:
    id: int
    message: str

@dataclass
class Clock:
    remaining: str