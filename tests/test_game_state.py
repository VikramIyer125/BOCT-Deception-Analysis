"""Tests for GameState, Player, and related data structures."""

import pytest

from botc.game_state import GameState, Player, Message, Nomination, AbilityInfo


def _make_players(n: int = 7) -> list[Player]:
    names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace"]
    chars = ["Washerwoman", "Empath", "Investigator", "Slayer", "Monk", "Poisoner", "Imp"]
    aligns = ["good", "good", "good", "good", "good", "evil", "evil"]
    return [
        Player(id=f"p{i}", name=names[i], character_name=chars[i], alignment=aligns[i])
        for i in range(n)
    ]


def _make_state(players: list[Player] | None = None) -> GameState:
    players = players or _make_players()
    return GameState(
        players=players,
        seating_order=[p.id for p in players],
    )


class TestPlayerLookup:
    def test_get_player(self):
        gs = _make_state()
        assert gs.get_player("p0").name == "Alice"

    def test_get_player_missing(self):
        gs = _make_state()
        with pytest.raises(ValueError):
            gs.get_player("nonexistent")

    def test_living_players(self):
        gs = _make_state()
        assert len(gs.living_players()) == 7
        gs.get_player("p0").alive = False
        assert len(gs.living_players()) == 6

    def test_dead_players(self):
        gs = _make_state()
        gs.get_player("p2").alive = False
        assert len(gs.dead_players()) == 1
        assert gs.dead_players()[0].id == "p2"


class TestNeighbours:
    def test_neighbours_circular(self):
        gs = _make_state()
        left, right = gs.get_neighbors("p0")
        assert left.id == "p6"
        assert right.id == "p1"

    def test_neighbours_skip_dead(self):
        gs = _make_state()
        gs.get_player("p6").alive = False
        left, right = gs.get_neighbors("p0")
        assert left.id == "p5"
        assert right.id == "p1"

    def test_neighbours_middle(self):
        gs = _make_state()
        left, right = gs.get_neighbors("p3")
        assert left.id == "p2"
        assert right.id == "p4"


class TestWinConditions:
    def test_good_wins_demon_dead(self):
        from botc.phases.storyteller import check_win_conditions
        gs = _make_state()
        gs.get_player("p6").alive = False  # Imp dies
        gs = check_win_conditions(gs)
        assert gs.winner == "good"

    def test_evil_wins_two_alive(self):
        from botc.phases.storyteller import check_win_conditions
        gs = _make_state()
        for i in range(5):
            gs.get_player(f"p{i}").alive = False
        gs = check_win_conditions(gs)
        assert gs.winner == "evil"

    def test_no_winner_yet(self):
        from botc.phases.storyteller import check_win_conditions
        gs = _make_state()
        gs = check_win_conditions(gs)
        assert gs.winner is None


class TestGameLog:
    def test_add_log_increments_turn(self):
        gs = _make_state()
        gs.add_log("p0", "night_1")
        gs.add_log("p1", "night_1")
        assert len(gs.game_log) == 2
        assert gs.game_log[0].turn == 1
        assert gs.game_log[1].turn == 2

    def test_log_entry_fields(self):
        gs = _make_state()
        gs.add_log(
            "p0", "day_1",
            observation={"phase": "day"},
            thinking="I think p5 is evil",
            action={"speech": "Hello"},
        )
        entry = gs.game_log[0]
        assert entry.player_id == "p0"
        assert entry.thinking == "I think p5 is evil"
        assert entry.action["speech"] == "Hello"


class TestSerialization:
    def test_player_to_dict(self):
        p = Player(id="p0", name="Alice", character_name="Empath", alignment="good")
        d = p.model_dump()
        assert d["id"] == "p0"
        assert d["name"] == "Alice"
        assert d["alive"] is True

    def test_game_state_to_dict(self):
        gs = _make_state()
        d = gs.model_dump()
        assert len(d["players"]) == 7
        assert d["phase"] == "setup"
