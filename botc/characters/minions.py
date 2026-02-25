from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from botc.characters.base import BaseCharacter, CharacterType, register_character

if TYPE_CHECKING:
    from botc.game_state import AbilityInfo, GameState, Player


@register_character
class Poisoner(BaseCharacter):
    name = "Poisoner"
    character_type = CharacterType.MINION
    ability_description = (
        "Each night, choose a player: they are poisoned tonight and tomorrow."
    )
    acts_on_first_night = True
    acts_on_other_nights = True
    night_action_priority = 1

    def get_night_action_prompt(
        self, game_state: "GameState", player: "Player"
    ) -> Optional[str]:
        others = [p.name for p in game_state.living_players() if p.id != player.id]
        return (
            "Choose a player to poison tonight and tomorrow.\n"
            f"Alive players (excluding you): {', '.join(others)}\n"
            "FORMAT: POISON: <player>"
        )

    def resolve_night_action(
        self,
        game_state: "GameState",
        player: "Player",
        action: Dict[str, Any],
    ) -> Tuple["GameState", Optional["AbilityInfo"]]:
        target_id = action.get("target")
        if target_id:
            game_state.poisoned_player = target_id
        return game_state, None
