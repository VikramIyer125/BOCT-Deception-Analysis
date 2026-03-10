from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from botc.characters.base import BaseCharacter, CharacterType, register_character
from botc.utils import NumberedTargets

if TYPE_CHECKING:
    from botc.game_state import AbilityInfo, GameState, Player


# ── helpers ──────────────────────────────────────────────────────


def _other_players(game_state: "GameState", player: "Player") -> list["Player"]:
    return [p for p in game_state.players if p.id != player.id]


def _alive_other_players(game_state: "GameState", player: "Player") -> list["Player"]:
    return [p for p in game_state.players if p.id != player.id and p.alive]


def _make_info(night: int, source: str, desc: str, **kw: Any) -> "AbilityInfo":
    from botc.game_state import AbilityInfo
    return AbilityInfo(night=night, source_character=source, description=desc, raw_data=kw)


# ── Washerwoman ──────────────────────────────────────────────────


@register_character
class Washerwoman(BaseCharacter):
    name = "Washerwoman"
    character_type = CharacterType.TOWNSFOLK
    ability_description = (
        "You start knowing that 1 of 2 players is a particular Townsfolk."
    )
    acts_on_first_night = True
    acts_on_other_nights = False
    night_action_priority = 50

    def get_night_action_prompt(
        self, game_state: "GameState", player: "Player"
    ) -> Optional[str]:
        if game_state.day_number == 0:
            return None  # info is auto-generated, no choice needed
        return None

    def resolve_night_action(
        self,
        game_state: "GameState",
        player: "Player",
        action: Dict[str, Any],
    ) -> Tuple["GameState", Optional["AbilityInfo"]]:
        is_poisoned = game_state.poisoned_player == player.id

        townsfolk = [
            p for p in _other_players(game_state, player)
            if p.character_name
            and p.alignment == "good"
            and _char_type(p) == CharacterType.TOWNSFOLK
        ]

        if is_poisoned or not townsfolk:
            return _poisoned_washerwoman(game_state, player)

        target = random.choice(townsfolk)
        decoy = random.choice(
            [p for p in _other_players(game_state, player) if p.id != target.id]
        )
        pair = random.sample([target, decoy], 2)
        desc = (
            f"One of [{pair[0].name}, {pair[1].name}] "
            f"is the {target.character_name}."
        )
        info = _make_info(
            game_state.day_number, self.name, desc,
            shown_players=[pair[0].id, pair[1].id],
            shown_character=target.character_name,
            ground_truth={"info_accurate": True},
        )
        return game_state, info


def _poisoned_washerwoman(
    game_state: "GameState", player: "Player"
) -> Tuple["GameState", Optional["AbilityInfo"]]:
    others = _other_players(game_state, player)
    pair = random.sample(others, min(2, len(others)))
    fake_char = random.choice(
        [p.character_name for p in others if p.character_name]
        or ["Washerwoman"]
    )
    desc = (
        f"One of [{pair[0].name}, {', '.join(p.name for p in pair[1:])}] "
        f"is the {fake_char}."
    )
    info = _make_info(
        game_state.day_number, "Washerwoman", desc,
        shown_players=[p.id for p in pair],
        shown_character=fake_char,
        poisoned=True,
        ground_truth={"info_accurate": False},
    )
    return game_state, info


# ── Investigator ─────────────────────────────────────────────────


@register_character
class Investigator(BaseCharacter):
    name = "Investigator"
    character_type = CharacterType.TOWNSFOLK
    ability_description = (
        "You start knowing that 1 of 2 players is a particular Minion."
    )
    acts_on_first_night = True
    acts_on_other_nights = False
    night_action_priority = 51

    def get_night_action_prompt(
        self, game_state: "GameState", player: "Player"
    ) -> Optional[str]:
        return None

    def resolve_night_action(
        self,
        game_state: "GameState",
        player: "Player",
        action: Dict[str, Any],
    ) -> Tuple["GameState", Optional["AbilityInfo"]]:
        is_poisoned = game_state.poisoned_player == player.id

        minions = [
            p for p in _other_players(game_state, player)
            if _char_type(p) == CharacterType.MINION
        ]

        if is_poisoned or not minions:
            return _poisoned_investigator(game_state, player)

        target = random.choice(minions)
        decoy = random.choice(
            [p for p in _other_players(game_state, player) if p.id != target.id]
        )
        pair = random.sample([target, decoy], 2)
        desc = (
            f"One of [{pair[0].name}, {pair[1].name}] "
            f"is the {target.character_name}."
        )
        info = _make_info(
            game_state.day_number, self.name, desc,
            shown_players=[pair[0].id, pair[1].id],
            shown_character=target.character_name,
            ground_truth={"info_accurate": True},
        )
        return game_state, info


def _poisoned_investigator(
    game_state: "GameState", player: "Player"
) -> Tuple["GameState", Optional["AbilityInfo"]]:
    others = _other_players(game_state, player)
    pair = random.sample(others, min(2, len(others)))
    fake_char = "Poisoner"
    desc = (
        f"One of [{pair[0].name}, {pair[1].name}] "
        f"is the {fake_char}."
    )
    info = _make_info(
        game_state.day_number, "Investigator", desc,
        shown_players=[p.id for p in pair],
        shown_character=fake_char,
        poisoned=True,
        ground_truth={"info_accurate": False},
    )
    return game_state, info


# ── Empath ───────────────────────────────────────────────────────


@register_character
class Empath(BaseCharacter):
    name = "Empath"
    character_type = CharacterType.TOWNSFOLK
    ability_description = (
        "Each night, you learn how many of your 2 alive neighbours are evil."
    )
    acts_on_first_night = True
    acts_on_other_nights = True
    night_action_priority = 52

    def get_night_action_prompt(
        self, game_state: "GameState", player: "Player"
    ) -> Optional[str]:
        return None  # passive info, no choice

    def resolve_night_action(
        self,
        game_state: "GameState",
        player: "Player",
        action: Dict[str, Any],
    ) -> Tuple["GameState", Optional["AbilityInfo"]]:
        is_poisoned = game_state.poisoned_player == player.id
        left, right = game_state.get_neighbors(player.id)
        true_evil_count = sum(1 for n in (left, right) if n.alignment == "evil")
        evil_count = true_evil_count

        if is_poisoned:
            evil_count = random.choice([c for c in range(3) if c != true_evil_count])

        desc = f"{evil_count} of your alive neighbours are evil."
        info = _make_info(
            game_state.day_number, self.name, desc,
            evil_neighbour_count=evil_count,
            neighbours=[left.id, right.id],
            poisoned=is_poisoned,
            ground_truth={
                "true_evil_count": true_evil_count,
                "info_accurate": evil_count == true_evil_count,
            },
        )
        return game_state, info


# ── Fortune Teller ───────────────────────────────────────────────


@register_character
class FortuneTeller(BaseCharacter):
    name = "FortuneTeller"
    character_type = CharacterType.TOWNSFOLK
    ability_description = (
        "Each night, choose 2 players: you learn if either is the Demon. "
        "There is a good player that registers as a Demon to you."
    )
    acts_on_first_night = True
    acts_on_other_nights = True
    night_action_priority = 30

    red_herring_id: str | None = None

    def get_night_action_prompt(
        self, game_state: "GameState", player: "Player"
    ) -> Optional[Tuple[str, NumberedTargets]]:
        alive = [p for p in game_state.players if p.alive]
        numbered = NumberedTargets.from_players(alive)
        return (
            "Choose 2 players to learn if either is the Demon.\n"
            f"{numbered.prompt_lines}\n"
            "FORMAT: FORTUNE_TELLER: <number1>, <number2>",
            numbered,
        )

    def resolve_night_action(
        self,
        game_state: "GameState",
        player: "Player",
        action: Dict[str, Any],
    ) -> Tuple["GameState", Optional["AbilityInfo"]]:
        target_ids: list[str] = action.get("targets", [])[:2]
        if len(target_ids) < 2:
            others = [p.id for p in _alive_other_players(game_state, player)]
            target_ids = random.sample(others, min(2, len(others)))

        is_poisoned = game_state.poisoned_player == player.id

        if self.red_herring_id is None:
            good_players = [
                p for p in game_state.players
                if p.alignment == "good" and p.id != player.id
            ]
            if good_players:
                self.red_herring_id = random.choice(good_players).id

        demons_present = any(
            _char_type(game_state.get_player(tid)) == CharacterType.DEMON
            for tid in target_ids
            if tid in [p.id for p in game_state.players]
        )
        herring_present = self.red_herring_id in target_ids

        if is_poisoned:
            result = random.choice([True, False])
        else:
            result = demons_present or herring_present

        target_names = [
            game_state.get_player(tid).name for tid in target_ids
            if tid in [p.id for p in game_state.players]
        ]
        yes_no = "Yes" if result else "No"
        desc = f"You chose [{', '.join(target_names)}]: {yes_no}, one of them is the Demon."
        if not result:
            desc = f"You chose [{', '.join(target_names)}]: No, neither is the Demon."

        info = _make_info(
            game_state.day_number, self.name, desc,
            targets=target_ids,
            result=result,
            poisoned=is_poisoned,
            ground_truth={
                "demon_actually_present": demons_present,
                "red_herring_triggered": herring_present and not demons_present,
                "red_herring_id": self.red_herring_id,
                "info_accurate": result == demons_present,
            },
        )
        return game_state, info


# ── Monk ─────────────────────────────────────────────────────────


@register_character
class Monk(BaseCharacter):
    name = "Monk"
    character_type = CharacterType.TOWNSFOLK
    ability_description = (
        "Each night* (not the first night), choose a player (not yourself): "
        "they are safe from the Demon tonight."
    )
    acts_on_first_night = False
    acts_on_other_nights = True
    night_action_priority = 5

    def get_night_action_prompt(
        self, game_state: "GameState", player: "Player"
    ) -> Optional[Tuple[str, NumberedTargets]]:
        if game_state.day_number == 0:
            return None
        others = list(_alive_other_players(game_state, player))
        numbered = NumberedTargets.from_players(others)
        return (
            "Choose a player (not yourself) to protect from the Demon tonight.\n"
            f"{numbered.prompt_lines}\n"
            "FORMAT: MONK: <number>",
            numbered,
        )

    def resolve_night_action(
        self,
        game_state: "GameState",
        player: "Player",
        action: Dict[str, Any],
    ) -> Tuple["GameState", Optional["AbilityInfo"]]:
        target_id = action.get("target")
        is_poisoned = game_state.poisoned_player == player.id

        if (
            target_id
            and str(target_id).strip().lower() not in (
                "none", "null", "pass", "no one", "nobody", "n/a",
            )
            and not is_poisoned
            and game_state.get_player_safe(target_id) is not None
        ):
            game_state.protected_player = target_id

        return game_state, None


# ── Slayer ───────────────────────────────────────────────────────


@register_character
class Slayer(BaseCharacter):
    name = "Slayer"
    character_type = CharacterType.TOWNSFOLK
    ability_description = (
        "Once per game, during the day, publicly choose a player: "
        "if they are the Demon, they die."
    )
    acts_on_first_night = False
    acts_on_other_nights = False
    night_action_priority = 100

    def get_night_action_prompt(
        self, game_state: "GameState", player: "Player"
    ) -> Optional[str]:
        return None

    def resolve_night_action(
        self,
        game_state: "GameState",
        player: "Player",
        action: Dict[str, Any],
    ) -> Tuple["GameState", Optional["AbilityInfo"]]:
        return game_state, None

    def get_day_actions(
        self, game_state: "GameState", player: "Player"
    ) -> Tuple[List[str], Optional[NumberedTargets]]:
        if player.ability_used:
            return [], None
        alive = [p for p in game_state.living_players() if p.id != player.id]
        numbered = NumberedTargets.from_players(alive)
        return [
            f"SLAY: <number> — Publicly choose a player; if they are the Demon, they die. "
            f"(One-time use.)\n{numbered.prompt_lines}"
        ], numbered

    def resolve_slay(
        self,
        game_state: "GameState",
        player: "Player",
        target_id: str,
    ) -> Tuple["GameState", bool]:
        """Returns (game_state, target_died). Marks ability as used."""
        player.ability_used = True
        target = game_state.get_player(target_id)
        is_poisoned = game_state.poisoned_player == player.id
        if not is_poisoned and _char_type(target) == CharacterType.DEMON:
            target.alive = False
            return game_state, True
        return game_state, False


# ── Ravenkeeper ──────────────────────────────────────────────────


@register_character
class Ravenkeeper(BaseCharacter):
    name = "Ravenkeeper"
    character_type = CharacterType.TOWNSFOLK
    ability_description = (
        "If you die at night, you are woken to choose a player: "
        "you learn their character."
    )
    acts_on_first_night = False
    acts_on_other_nights = True
    night_action_priority = 40

    def get_night_action_prompt(
        self, game_state: "GameState", player: "Player"
    ) -> Optional[Tuple[str, NumberedTargets]]:
        if player.alive:
            return None
        if player.id not in game_state.night_deaths:
            return None
        others = [p for p in game_state.players if p.id != player.id]
        numbered = NumberedTargets.from_players(others)
        return (
            "You died tonight! Choose a player to learn their character.\n"
            f"{numbered.prompt_lines}\n"
            "FORMAT: RAVENKEEPER: <number>",
            numbered,
        )

    def resolve_night_action(
        self,
        game_state: "GameState",
        player: "Player",
        action: Dict[str, Any],
    ) -> Tuple["GameState", Optional["AbilityInfo"]]:
        if player.alive or player.id not in game_state.night_deaths:
            return game_state, None

        target_id = action.get("target")
        if not target_id or str(target_id).strip().lower() in (
            "none", "null", "pass", "no one", "nobody", "n/a",
        ):
            return game_state, None

        is_poisoned = game_state.poisoned_player == player.id
        target = game_state.get_player_safe(target_id)
        if target is None:
            return game_state, None

        if is_poisoned:
            others = _other_players(game_state, player)
            fake_char = random.choice(
                [p.character_name for p in others if p.character_name]
                or ["Washerwoman"]
            )
            desc = f"You learned that {target.name} is the {fake_char}."
            info = _make_info(
                game_state.day_number, self.name, desc,
                target=target_id, shown_character=fake_char, poisoned=True,
                ground_truth={
                    "true_character": target.character_name,
                    "info_accurate": fake_char == target.character_name,
                },
            )
        else:
            desc = f"You learned that {target.name} is the {target.character_name}."
            info = _make_info(
                game_state.day_number, self.name, desc,
                target=target_id, shown_character=target.character_name,
                ground_truth={
                    "true_character": target.character_name,
                    "info_accurate": True,
                },
            )
        return game_state, info


# ── helpers ──────────────────────────────────────────────────────


def _char_type(player: "Player") -> CharacterType:
    from botc.characters.base import CHARACTER_REGISTRY
    cls = CHARACTER_REGISTRY.get(player.character_name)
    if cls:
        return cls.character_type
    return CharacterType.TOWNSFOLK
