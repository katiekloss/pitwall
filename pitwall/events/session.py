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
    messages: List[str]