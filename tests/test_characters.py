"""Tests for character abilities and resolution."""

import random

import pytest

from botc.game_state import GameState, Player
from botc.characters import CHARACTER_REGISTRY
from botc.characters.base import CharacterType
from botc.characters.townsfolk import (
    Washerwoman,
    Investigator,
    Empath,
    FortuneTeller,
    Monk,
    Slayer,
    Ravenkeeper,
)
from botc.characters.minions import Poisoner
from botc.characters.demons import Imp


def _make_players() -> list[Player]:
    specs = [
        ("p0", "Alice", "Washerwoman", "good"),
        ("p1", "Bob", "Empath", "good"),
        ("p2", "Charlie", "Investigator", "good"),
        ("p3", "Diana", "Slayer", "good"),
        ("p4", "Eve", "Monk", "good"),
        ("p5", "Frank", "Poisoner", "evil"),
        ("p6", "Grace", "Imp", "evil"),
    ]
    return [
        Player(id=pid, name=name, character_name=char, alignment=align)
        for pid, name, char, align in specs
    ]


def _make_state() -> GameState:
    players = _make_players()
    return GameState(
        players=players,
        seating_order=[p.id for p in players],
        day_number=0,
    )


class TestCharacterRegistry:
    def test_all_characters_registered(self):
        expected = {
            "Washerwoman", "Investigator", "Empath", "FortuneTeller",
            "Monk", "Slayer", "Ravenkeeper", "Poisoner", "Imp",
        }
        assert expected.issubset(set(CHARACTER_REGISTRY.keys()))

    def test_alignments(self):
        for name, cls in CHARACTER_REGISTRY.items():
            instance = cls()
            if cls.character_type in (CharacterType.TOWNSFOLK, CharacterType.OUTSIDER):
                assert instance.alignment == "good", f"{name} should be good"
            else:
                assert instance.alignment == "evil", f"{name} should be evil"


class TestWasherwoman:
    def test_correct_info(self):
        random.seed(42)
        gs = _make_state()
        char = Washerwoman()
        gs, info = char.resolve_night_action(gs, gs.get_player("p0"), {})
        assert info is not None
        assert info.source_character == "Washerwoman"
        assert "is the" in info.description

    def test_poisoned_gives_false_info(self):
        random.seed(42)
        gs = _make_state()
        gs.poisoned_player = "p0"
        char = Washerwoman()
        gs, info = char.resolve_night_action(gs, gs.get_player("p0"), {})
        assert info is not None
        assert info.raw_data.get("poisoned") is True


class TestInvestigator:
    def test_correct_info(self):
        random.seed(42)
        gs = _make_state()
        char = Investigator()
        gs, info = char.resolve_night_action(gs, gs.get_player("p2"), {})
        assert info is not None
        assert "Poisoner" in info.description

    def test_poisoned(self):
        random.seed(42)
        gs = _make_state()
        gs.poisoned_player = "p2"
        char = Investigator()
        gs, info = char.resolve_night_action(gs, gs.get_player("p2"), {})
        assert info is not None
        assert info.raw_data.get("poisoned") is True


class TestEmpath:
    def test_no_evil_neighbours(self):
        random.seed(42)
        gs = _make_state()
        char = Empath()
        gs, info = char.resolve_night_action(gs, gs.get_player("p1"), {})
        assert info is not None
        assert "0" in info.description

    def test_evil_neighbour(self):
        random.seed(42)
        gs = _make_state()
        char = Empath()
        gs, info = char.resolve_night_action(gs, gs.get_player("p4"), {})
        assert info is not None
        count = info.raw_data["evil_neighbour_count"]
        assert count >= 1  # p5 (Poisoner) is a neighbour

    def test_poisoned_empath(self):
        random.seed(42)
        gs = _make_state()
        gs.poisoned_player = "p1"
        char = Empath()
        gs, info = char.resolve_night_action(gs, gs.get_player("p1"), {})
        assert info is not None
        assert info.raw_data.get("poisoned") is True


class TestPoisoner:
    def test_poisons_target(self):
        gs = _make_state()
        char = Poisoner()
        gs, info = char.resolve_night_action(gs, gs.get_player("p5"), {"target": "p0"})
        assert gs.poisoned_player == "p0"
        assert info is None


class TestMonk:
    def test_protects_target(self):
        gs = _make_state()
        gs.day_number = 1
        char = Monk()
        gs, info = char.resolve_night_action(gs, gs.get_player("p4"), {"target": "p0"})
        assert gs.protected_player == "p0"

    def test_no_action_first_night(self):
        gs = _make_state()
        gs.day_number = 0
        char = Monk()
        prompt = char.get_night_action_prompt(gs, gs.get_player("p4"))
        assert prompt is None

    def test_poisoned_monk(self):
        gs = _make_state()
        gs.day_number = 1
        gs.poisoned_player = "p4"
        char = Monk()
        gs, info = char.resolve_night_action(gs, gs.get_player("p4"), {"target": "p0"})
        assert gs.protected_player is None


class TestImp:
    def test_kills_target(self):
        gs = _make_state()
        gs.day_number = 1
        char = Imp()
        gs, info = char.resolve_night_action(gs, gs.get_player("p6"), {"target": "p0"})
        assert not gs.get_player("p0").alive
        assert "p0" in gs.night_deaths

    def test_monk_protection(self):
        gs = _make_state()
        gs.day_number = 1
        gs.protected_player = "p0"
        char = Imp()
        gs, info = char.resolve_night_action(gs, gs.get_player("p6"), {"target": "p0"})
        assert gs.get_player("p0").alive

    def test_starpass(self):
        gs = _make_state()
        gs.day_number = 1
        char = Imp()
        gs, info = char.resolve_night_action(gs, gs.get_player("p6"), {"target": "p6"})
        assert not gs.get_player("p6").alive
        assert gs.get_player("p5").character_name == "Imp"

    def test_no_action_first_night(self):
        gs = _make_state()
        gs.day_number = 0
        char = Imp()
        prompt = char.get_night_action_prompt(gs, gs.get_player("p6"))
        assert prompt is None


class TestSlayer:
    def test_slay_demon(self):
        gs = _make_state()
        char = Slayer()
        gs, died = char.resolve_slay(gs, gs.get_player("p3"), "p6")
        assert died
        assert not gs.get_player("p6").alive
        assert gs.get_player("p3").ability_used

    def test_slay_non_demon(self):
        gs = _make_state()
        char = Slayer()
        gs, died = char.resolve_slay(gs, gs.get_player("p3"), "p1")
        assert not died
        assert gs.get_player("p1").alive
        assert gs.get_player("p3").ability_used

    def test_slay_while_poisoned(self):
        gs = _make_state()
        gs.poisoned_player = "p3"
        char = Slayer()
        gs, died = char.resolve_slay(gs, gs.get_player("p3"), "p6")
        assert not died
        assert gs.get_player("p6").alive


class TestRavenkeeper:
    def test_learns_character_on_death(self):
        random.seed(42)
        gs = _make_state()
        gs.get_player("p0").character_name = "Ravenkeeper"
        gs.get_player("p0").alive = False
        gs.night_deaths = ["p0"]
        char = Ravenkeeper()
        gs, info = char.resolve_night_action(
            gs, gs.get_player("p0"), {"target": "p6"}
        )
        assert info is not None
        assert "Imp" in info.description

    def test_poisoned_ravenkeeper(self):
        random.seed(42)
        gs = _make_state()
        gs.get_player("p0").character_name = "Ravenkeeper"
        gs.get_player("p0").alive = False
        gs.night_deaths = ["p0"]
        gs.poisoned_player = "p0"
        char = Ravenkeeper()
        gs, info = char.resolve_night_action(
            gs, gs.get_player("p0"), {"target": "p6"}
        )
        assert info is not None
        assert info.raw_data.get("poisoned") is True


class TestFortuneTeller:
    def test_detects_demon(self):
        random.seed(42)
        gs = _make_state()
        char = FortuneTeller()
        char.red_herring_id = "p99"  # non-existent, so no false positive
        gs, info = char.resolve_night_action(
            gs, gs.get_player("p1"), {"targets": ["p6", "p0"]}
        )
        assert info is not None
        assert info.raw_data["result"] is True

    def test_no_demon(self):
        random.seed(42)
        gs = _make_state()
        char = FortuneTeller()
        char.red_herring_id = "p99"
        gs, info = char.resolve_night_action(
            gs, gs.get_player("p1"), {"targets": ["p0", "p2"]}
        )
        assert info is not None
        assert info.raw_data["result"] is False

    def test_red_herring(self):
        random.seed(42)
        gs = _make_state()
        char = FortuneTeller()
        char.red_herring_id = "p0"
        gs, info = char.resolve_night_action(
            gs, gs.get_player("p1"), {"targets": ["p0", "p2"]}
        )
        assert info is not None
        assert info.raw_data["result"] is True
