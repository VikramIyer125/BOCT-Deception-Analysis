from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from botc.game_state import Player


@dataclass
class NumberedTargets:
    """Numbered list of targets for constrained LLM output. Model returns a number."""

    prompt_lines: str  # "1. Alice\n2. Bob\n..."
    id_map: dict[int, str]  # {1: "p0", 2: "p1", ...}

    @classmethod
    def from_players(cls, players: List["Player"]) -> "NumberedTargets":
        lines = "\n".join(f"  {i + 1}. {p.name}" for i, p in enumerate(players))
        id_map = {i + 1: p.id for i, p in enumerate(players)}
        return cls(prompt_lines=lines, id_map=id_map)


PLAYER_NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace",
    "Hank", "Ivy", "Jack", "Kate", "Leo", "Mia", "Nick", "Olive",
]
