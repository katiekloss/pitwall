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
class RaceControlMessage:
    category: str
    flag: str
    scope: str
    message: str
    lap: int
    sector: int

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