from dataclasses import dataclass

@dataclass
class SessionChange:
    name: str
    part: str
    status: str