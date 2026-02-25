"""Automated storyteller logic — night ordering, win conditions, death announcements."""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from botc.characters import CHARACTER_REGISTRY
from botc.characters.base import CharacterType

if TYPE_CHECKING:
    from botc.game_state import GameState, Player


# ── Night action ordering ────────────────────────────────────────


def get_night_action_order(game_state: "GameState", first_night: bool) -> List["Player"]:
    """Return players that act tonight, sorted by priority (low = first)."""
    acting: list[tuple[int, "Player"]] = []
    for player in game_state.players:
        cls = CHARACTER_REGISTRY.get(player.character_name)
        if cls is None:
            continue
        if first_night and cls.acts_on_first_night:
            acting.append((cls.night_action_priority, player))
        elif not first_night and cls.acts_on_other_nights:
            acting.append((cls.night_action_priority, player))

    acting.sort(key=lambda t: t[0])
    return [p for _, p in acting]


# ── Win conditions ───────────────────────────────────────────────


def check_win_conditions(game_state: "GameState") -> "GameState":
    """Check and set game_state.winner if a team has won."""

    alive = game_state.living_players()

    demon_alive = any(
        CHARACTER_REGISTRY.get(p.character_name) is not None
        and CHARACTER_REGISTRY[p.character_name].character_type == CharacterType.DEMON
        for p in alive
    )

    if not demon_alive:
        game_state.winner = "good"
        game_state.phase = "ended"
        return game_state

    if len(alive) <= 2:
        game_state.winner = "evil"
        game_state.phase = "ended"
        return game_state

    return game_state


# ── Death announcements ──────────────────────────────────────────


def announce_deaths(game_state: "GameState") -> str:
    """Return a narrative string announcing night deaths."""
    if not game_state.night_deaths:
        return "The town wakes up. No one died during the night."

    names = []
    for pid in game_state.night_deaths:
        names.append(game_state.get_player(pid).name)
    return (
        "The town wakes up. "
        + ", ".join(names)
        + (" has" if len(names) == 1 else " have")
        + " died during the night."
    )
