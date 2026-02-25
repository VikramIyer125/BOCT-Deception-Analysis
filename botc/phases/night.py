"""Night phase processing — first night and subsequent nights."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict, Optional

from botc.characters import CHARACTER_REGISTRY
from botc.characters.base import CharacterType
from botc.phases.storyteller import get_night_action_order

if TYPE_CHECKING:
    from botc.game_state import GameState


def run_first_night(
    game_state: "GameState",
    get_agent_action: Callable,
) -> "GameState":
    """Process first night: evil knowledge already set in setup, resolve first-night abilities."""

    game_state.phase = "night"
    game_state.day_number = 0
    game_state.night_deaths = []
    game_state.protected_player = None

    acting = get_night_action_order(game_state, first_night=True)

    for player in acting:
        if not player.alive:
            continue
        char_cls = CHARACTER_REGISTRY.get(player.character_name)
        if char_cls is None:
            continue
        char = char_cls()
        prompt = char.get_night_action_prompt(game_state, player)

        if prompt is not None:
            action_dict = get_agent_action(player.id, game_state, "night_action", prompt)
        else:
            action_dict = {}

        game_state, info = char.resolve_night_action(game_state, player, action_dict)
        if info:
            player.received_info.append(info)

    return game_state


def run_night_phase(
    game_state: "GameState",
    get_agent_action: Callable,
) -> "GameState":
    """Process a regular (non-first) night."""

    game_state.phase = "night"
    game_state.day_number += 1
    game_state.night_deaths = []
    game_state.protected_player = None

    acting = get_night_action_order(game_state, first_night=False)

    for player in acting:
        if not player.alive:
            # Ravenkeeper acts after dying, but only if just died this night
            char_cls = CHARACTER_REGISTRY.get(player.character_name)
            if char_cls is None:
                continue
            if player.id not in game_state.night_deaths:
                continue
            # fall through for Ravenkeeper
        char_cls = CHARACTER_REGISTRY.get(player.character_name)
        if char_cls is None:
            continue
        char = char_cls()
        prompt = char.get_night_action_prompt(game_state, player)

        if prompt is not None:
            action_dict = get_agent_action(player.id, game_state, "night_action", prompt)
        else:
            action_dict = {}

        game_state, info = char.resolve_night_action(game_state, player, action_dict)
        if info:
            player.received_info.append(info)

    return game_state
