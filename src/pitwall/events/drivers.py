from dataclasses import dataclass

@dataclass
class Driver:
    number: int
    broadcast_name: str
    initials: str
    team_name: str
    team_color: str
    """Hex code for the team's primary color"""
    first_name: str
    last_name: str