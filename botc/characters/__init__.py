"""Import all character modules so they register themselves."""

from botc.characters.base import CHARACTER_REGISTRY, BaseCharacter, CharacterType  # noqa: F401
from botc.characters.townsfolk import (  # noqa: F401
    Washerwoman,
    Investigator,
    Empath,
    FortuneTeller,
    Monk,
    Slayer,
    Ravenkeeper,
)
from botc.characters.minions import Poisoner  # noqa: F401
from botc.characters.demons import Imp  # noqa: F401
