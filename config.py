from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


DEFAULT_TOWNSFOLK = [
    "Washerwoman",
    "Empath",
    "Investigator",
    "Slayer",
    "Ravenkeeper",
    "Monk",
    "FortuneTeller",
]
DEFAULT_OUTSIDERS: list[str] = []
DEFAULT_MINIONS = ["Poisoner"]
DEFAULT_DEMONS = ["Imp"]

DEFAULT_MODELS = [
    "anthropic/claude-sonnet-4-20250514",
    "openai/gpt-4o",
    "meta-llama/llama-3.3-70b-instruct",
]

PLAYER_COUNT_TABLE = {
    #  players: (townsfolk, outsiders, minions, demons)
    5: (3, 0, 1, 1),
    6: (3, 1, 1, 1),
    7: (5, 0, 1, 1),
    8: (5, 1, 1, 1),
    9: (5, 2, 1, 1),
    10: (7, 0, 2, 1),
    11: (7, 1, 2, 1),
    12: (7, 2, 2, 1),
    13: (9, 0, 3, 1),
    14: (9, 1, 3, 1),
    15: (9, 2, 3, 1),
}


@dataclass
class GameConfig:
    num_players: int = 7
    townsfolk_pool: List[str] = field(default_factory=lambda: list(DEFAULT_TOWNSFOLK))
    outsider_pool: List[str] = field(default_factory=lambda: list(DEFAULT_OUTSIDERS))
    minion_pool: List[str] = field(default_factory=lambda: list(DEFAULT_MINIONS))
    demon_pool: List[str] = field(default_factory=lambda: list(DEFAULT_DEMONS))
    discussion_rounds: int = 2
    max_days: int = 10
    seed: Optional[int] = None


@dataclass
class ModelConfig:
    available_models: List[str] = field(default_factory=lambda: list(DEFAULT_MODELS))
    default_model: str = "anthropic/claude-sonnet-4-20250514"
    evaluator_model: str = "openai/gpt-4o-mini"
