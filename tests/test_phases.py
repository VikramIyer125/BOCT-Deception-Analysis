"""Tests for phase logic — night ordering, day voting, execution."""

import random
from typing import Any, Dict, List

import pytest

from botc.game_state import GameState, Player, Nomination
from botc.phases.storyteller import get_night_action_order, check_win_conditions, announce_deaths
from botc.phases.night import run_first_night, run_night_phase
from botc.phases.day import _resolve_execution


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


class TestNightActionOrder:
    def test_first_night_order(self):
        gs = _make_state()
        acting = get_night_action_order(gs, first_night=True)
        names = [p.character_name for p in acting]
        assert "Poisoner" in names
        assert "Washerwoman" in names
        assert "Empath" in names
        assert "Investigator" in names
        assert names.index("Poisoner") < names.index("Washerwoman")

    def test_other_night_order(self):
        gs = _make_state()
        gs.day_number = 1
        acting = get_night_action_order(gs, first_night=False)
        names = [p.character_name for p in acting]
        assert "Poisoner" in names
        assert "Monk" in names
        assert "Imp" in names
        assert "Empath" in names
        assert names.index("Poisoner") < names.index("Monk")
        assert names.index("Monk") < names.index("Imp")

    def test_imp_not_on_first_night(self):
        gs = _make_state()
        acting = get_night_action_order(gs, first_night=True)
        names = [p.character_name for p in acting]
        assert "Imp" not in names

    def test_monk_not_on_first_night(self):
        gs = _make_state()
        acting = get_night_action_order(gs, first_night=True)
        names = [p.character_name for p in acting]
        assert "Monk" not in names


class TestFirstNight:
    def test_first_night_runs(self):
        random.seed(42)
        gs = _make_state()

        def mock_agent(pid, gs, ctx, actions, numbered_targets=None):
            return {"target": "p0"}

        gs = run_first_night(gs, mock_agent)
        assert gs.phase == "night"
        assert gs.day_number == 0


class TestAnnounceDeaths:
    def test_no_deaths(self):
        gs = _make_state()
        msg = announce_deaths(gs)
        assert "No one died" in msg

    def test_one_death(self):
        gs = _make_state()
        gs.night_deaths = ["p0"]
        msg = announce_deaths(gs)
        assert "Alice" in msg
        assert "has died" in msg

    def test_multiple_deaths(self):
        gs = _make_state()
        gs.night_deaths = ["p0", "p1"]
        msg = announce_deaths(gs)
        assert "Alice" in msg
        assert "Bob" in msg
        assert "have died" in msg


class TestExecution:
    def test_majority_executes(self):
        gs = _make_state()
        nom = Nomination(
            id="n1",
            nominator_id="p0",
            nominee_id="p6",
            votes_for=["p0", "p1", "p2", "p3"],
            votes_against=["p4", "p5", "p6"],
            resolved=True,
        )
        gs.nominations = [nom]
        gs = _resolve_execution(gs)
        assert gs.executed_today == "p6"
        assert not gs.get_player("p6").alive

    def test_no_majority_no_execution(self):
        gs = _make_state()
        nom = Nomination(
            id="n1",
            nominator_id="p0",
            nominee_id="p6",
            votes_for=["p0", "p1"],
            votes_against=["p2", "p3", "p4", "p5", "p6"],
            resolved=True,
        )
        gs.nominations = [nom]
        gs = _resolve_execution(gs)
        assert gs.executed_today is None
        assert gs.get_player("p6").alive

    def test_highest_votes_wins(self):
        gs = _make_state()
        nom1 = Nomination(
            id="n1",
            nominator_id="p0",
            nominee_id="p5",
            votes_for=["p0", "p1", "p2", "p3"],
            votes_against=["p4", "p5", "p6"],
            resolved=True,
        )
        nom2 = Nomination(
            id="n2",
            nominator_id="p1",
            nominee_id="p6",
            votes_for=["p0", "p1", "p2", "p3", "p4"],
            votes_against=["p5", "p6"],
            resolved=True,
        )
        gs.nominations = [nom1, nom2]
        gs = _resolve_execution(gs)
        assert gs.executed_today == "p6"


class TestElo:
    def test_elo_update_win(self):
        from evaluation.elo import update_elo
        new = update_elo(1500, 1500, won=True)
        assert new > 1500

    def test_elo_update_loss(self):
        from evaluation.elo import update_elo
        new = update_elo(1500, 1500, won=False)
        assert new < 1500

    def test_elo_from_games(self):
        from evaluation.elo import calculate_elo_from_games, GameResult, PlayerResult
        results = [
            GameResult(
                winner="good",
                players=[
                    PlayerResult("p0", "model-a", "good", "Washerwoman"),
                    PlayerResult("p1", "model-a", "good", "Empath"),
                    PlayerResult("p2", "model-b", "good", "Investigator"),
                    PlayerResult("p3", "model-b", "good", "Slayer"),
                    PlayerResult("p4", "model-a", "good", "Monk"),
                    PlayerResult("p5", "model-b", "evil", "Poisoner"),
                    PlayerResult("p6", "model-a", "evil", "Imp"),
                ],
            ),
        ]
        elo = calculate_elo_from_games(results)
        assert "model-a" in elo.deception_elo
        assert "model-b" in elo.detection_elo


class TestActionParser:
    def test_parse_agent_response(self):
        from agents.prompts.action_parser import parse_agent_response
        text = """
[Condensed Memory]
I know that Bob is suspicious.

[Thinking Process]
I think the Imp is either Bob or Frank.

[Action]
SPEAK: I believe Bob is evil and we should nominate him.
"""
        result = parse_agent_response(text)
        assert result.parse_success
        assert "Bob is suspicious" in result.condensed_memory
        assert "Imp" in result.thinking_process
        assert "SPEAK" in result.action

    def test_parse_night_action(self):
        from agents.prompts.action_parser import parse_night_action
        gs = _make_state()
        result = parse_night_action("KILL: Alice", gs)
        assert result.get("target") == "p0"

    def test_parse_vote_yes(self):
        from agents.prompts.action_parser import parse_day_action
        result = parse_day_action("YES")
        assert result.get("vote") is True

    def test_parse_vote_no(self):
        from agents.prompts.action_parser import parse_day_action
        result = parse_day_action("NO")
        assert result.get("vote") is False

    def test_parse_nomination(self):
        from agents.prompts.action_parser import parse_day_action
        gs = _make_state()
        result = parse_day_action("NOMINATE: Grace", gs)
        assert result.get("nominate") == "p6"

    def test_parse_fortune_teller(self):
        from agents.prompts.action_parser import parse_night_action
        gs = _make_state()
        result = parse_night_action("FORTUNE_TELLER: Alice, Bob", gs)
        assert result.get("targets") == ["p0", "p1"]
