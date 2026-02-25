from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from botc.game_state import AbilityInfo, GameState, Player


class CharacterType(Enum):
    TOWNSFOLK = "townsfolk"
    OUTSIDER = "outsider"
    MINION = "minion"
    DEMON = "demon"


class BaseCharacter(ABC):
    name: str
    character_type: CharacterType
    ability_description: str

    acts_on_first_night: bool = False
    acts_on_other_nights: bool = False
    night_action_priority: int = 100  # lower = earlier

    @property
    def alignment(self) -> str:
        if self.character_type in (CharacterType.TOWNSFOLK, CharacterType.OUTSIDER):
            return "good"
        return "evil"

    @abstractmethod
    def get_night_action_prompt(
        self, game_state: GameState, player: Player
    ) -> Optional[str]:
        """Return action prompt string, or None if no action this night."""
        ...

    @abstractmethod
    def resolve_night_action(
        self,
        game_state: GameState,
        player: Player,
        action: Dict[str, Any],
    ) -> Tuple[GameState, Optional[AbilityInfo]]:
        """Mutate *game_state* in place and return (game_state, info_for_player)."""
        ...

    def get_day_actions(
        self, game_state: GameState, player: Player
    ) -> List[str]:
        return []


CHARACTER_REGISTRY: Dict[str, type[BaseCharacter]] = {}


def register_character(cls: type[BaseCharacter]) -> type[BaseCharacter]:
    CHARACTER_REGISTRY[cls.name] = cls
    return cls
