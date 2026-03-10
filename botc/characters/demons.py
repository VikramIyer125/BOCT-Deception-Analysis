from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from botc.characters.base import BaseCharacter, CharacterType, register_character
from botc.utils import NumberedTargets

if TYPE_CHECKING:
    from botc.game_state import AbilityInfo, GameState, Player


@register_character
class Imp(BaseCharacter):
    name = "Imp"
    character_type = CharacterType.DEMON
    ability_description = (
        "Each night* (not the first night), choose a player: they die. "
        "If you kill yourself, a Minion becomes the Imp."
    )
    acts_on_first_night = False
    acts_on_other_nights = True
    night_action_priority = 20

    def get_night_action_prompt(
        self, game_state: "GameState", player: "Player"
    ) -> Optional[Tuple[str, NumberedTargets]]:
        if game_state.day_number == 0:
            return None
        targets = game_state.living_players()
        numbered = NumberedTargets.from_players(targets)
        return (
            "Choose a player to kill tonight (you may choose yourself to "
            "pass the Demon role to your Minion).\n"
            f"{numbered.prompt_lines}\n"
            "FORMAT: KILL: <number>",
            numbered,
        )

    def resolve_night_action(
        self,
        game_state: "GameState",
        player: "Player",
        action: Dict[str, Any],
    ) -> Tuple["GameState", Optional["AbilityInfo"]]:
        target_id = action.get("target")
        if not target_id or str(target_id).strip().lower() in (
            "none", "null", "pass", "no one", "nobody", "n/a",
        ):
            return game_state, None

        if target_id == game_state.protected_player:
            return game_state, None

        target = game_state.get_player_safe(target_id)
        if target is None:
            return game_state, None

        if target_id == player.id:
            return self._starpass(game_state, player)

        target.alive = False
        game_state.night_deaths.append(target_id)
        return game_state, None

    # ── Imp self-kill (starpass) ──────────────────────────────────

    @staticmethod
    def _starpass(
        game_state: "GameState", imp_player: "Player"
    ) -> Tuple["GameState", Optional["AbilityInfo"]]:
        """Imp kills itself; a living Minion becomes the new Imp."""
        from botc.characters.base import CHARACTER_REGISTRY

        minions = [
            p for p in game_state.living_players()
            if p.id != imp_player.id and p.alignment == "evil"
        ]

        if not minions:
            imp_player.alive = False
            game_state.night_deaths.append(imp_player.id)
            return game_state, None

        new_imp = minions[0]
        imp_player.alive = False
        game_state.night_deaths.append(imp_player.id)

        new_imp.character_name = "Imp"

        return game_state, None
