from __future__ import annotations

import random
from typing import Dict, List

from config import PLAYER_COUNT_TABLE, GameConfig
from botc.characters import CHARACTER_REGISTRY
from botc.characters.base import CharacterType
from botc.game_state import GameState, Player
from botc.utils import PLAYER_NAMES


def setup_game(
    player_models: Dict[str, str],
    config: GameConfig,
) -> GameState:
    """Create initial GameState with assigned roles and seating."""

    num = config.num_players
    if num not in PLAYER_COUNT_TABLE:
        raise ValueError(f"Unsupported player count: {num}")

    n_townsfolk, n_outsiders, n_minions, n_demons = PLAYER_COUNT_TABLE[num]

    townsfolk_chars = random.sample(config.townsfolk_pool, n_townsfolk)
    outsider_chars = random.sample(config.outsider_pool, n_outsiders) if n_outsiders else []
    minion_chars = random.sample(config.minion_pool, n_minions)
    demon_chars = random.sample(config.demon_pool, n_demons)

    all_chars = townsfolk_chars + outsider_chars + minion_chars + demon_chars
    random.shuffle(all_chars)

    player_ids = list(player_models.keys())
    names = PLAYER_NAMES[:num]
    random.shuffle(names)

    players: List[Player] = []
    for i, pid in enumerate(player_ids):
        char_name = all_chars[i]
        char_cls = CHARACTER_REGISTRY[char_name]
        alignment = char_cls.alignment
        players.append(
            Player(
                id=pid,
                name=names[i],
                character_name=char_name,
                alignment=alignment,
            )
        )

    seating_order = [p.id for p in players]
    random.shuffle(seating_order)

    state = GameState(players=players, seating_order=seating_order)

    _setup_evil_knowledge(state, config)

    return state


def _setup_evil_knowledge(state: GameState, config: GameConfig) -> None:
    """Give evil players knowledge of each other and demon bluffs."""
    evil_players = [p for p in state.players if p.alignment == "evil"]
    evil_ids = [p.id for p in evil_players]

    for p in evil_players:
        p.known_evil_players = [eid for eid in evil_ids if eid != p.id]

    in_play = {p.character_name for p in state.players}
    all_good = set(config.townsfolk_pool + config.outsider_pool)
    not_in_play = list(all_good - in_play)
    random.shuffle(not_in_play)

    bluffs = not_in_play[:3]

    demons = [p for p in evil_players if CHARACTER_REGISTRY[p.character_name].character_type == CharacterType.DEMON]
    for demon in demons:
        demon.demon_bluffs = bluffs
