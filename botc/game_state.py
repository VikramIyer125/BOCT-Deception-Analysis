from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class AbilityInfo(BaseModel):
    """Information a player received from their ability."""

    night: int
    source_character: str
    description: str
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    player_id: str
    content: str
    phase: str  # e.g. "day_1_round_1"
    timestamp: int  # turn counter


class Nomination(BaseModel):
    id: str
    nominator_id: str
    nominee_id: str
    votes_for: List[str] = Field(default_factory=list)
    votes_against: List[str] = Field(default_factory=list)
    resolved: bool = False


class LogEntry(BaseModel):
    turn: int
    phase: str
    player_id: str
    observation: Dict[str, Any] = Field(default_factory=dict)
    thinking: str = ""
    action: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None


class Player(BaseModel):
    id: str
    name: str
    character_name: str = ""
    alignment: Literal["good", "evil"] = "good"
    alive: bool = True
    ghost_vote_used: bool = False

    ability_used: bool = False  # one-time abilities like Slayer
    received_info: List[AbilityInfo] = Field(default_factory=list)

    known_evil_players: List[str] = Field(default_factory=list)
    demon_bluffs: List[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class GameState(BaseModel):
    players: List[Player] = Field(default_factory=list)
    seating_order: List[str] = Field(default_factory=list)  # player ids clockwise

    phase: Literal["night", "day", "setup", "ended"] = "setup"
    day_number: int = 0

    night_deaths: List[str] = Field(default_factory=list)
    protected_player: Optional[str] = None
    poisoned_player: Optional[str] = None

    discussion_transcript: List[Message] = Field(default_factory=list)
    nominations: List[Nomination] = Field(default_factory=list)
    executed_today: Optional[str] = None

    winner: Optional[Literal["good", "evil"]] = None

    game_log: List[LogEntry] = Field(default_factory=list)
    turn_counter: int = 0

    # ── helpers ──────────────────────────────────────────────

    def get_player(self, player_id: str) -> Player:
        for p in self.players:
            if p.id == player_id:
                return p
        cleaned = re.sub(r"[^a-zA-Z0-9 ]", "", player_id).strip().lower()
        for p in self.players:
            if p.id.lower() == cleaned or p.name.lower() == cleaned:
                return p
        raise ValueError(f"No player with id {player_id!r}")

    def living_players(self) -> List[Player]:
        return [p for p in self.players if p.alive]

    def living_player_ids(self) -> List[str]:
        return [p.id for p in self.players if p.alive]

    def dead_players(self) -> List[Player]:
        return [p for p in self.players if not p.alive]

    def living_players_in_seating_order(self) -> List[Player]:
        order = {pid: i for i, pid in enumerate(self.seating_order)}
        return sorted(self.living_players(), key=lambda p: order.get(p.id, 0))

    def all_players_in_seating_order(self) -> List[Player]:
        order = {pid: i for i, pid in enumerate(self.seating_order)}
        return sorted(self.players, key=lambda p: order.get(p.id, 0))

    def get_neighbors(self, player_id: str) -> tuple[Player, Player]:
        """Return (left_neighbor, right_neighbor) among *alive* players."""
        alive_ids = [
            pid for pid in self.seating_order
            if self.get_player(pid).alive
        ]
        if player_id not in alive_ids:
            alive_ids_with_target = [
                pid for pid in self.seating_order
                if self.get_player(pid).alive or pid == player_id
            ]
            idx = alive_ids_with_target.index(player_id)
            n = len(alive_ids_with_target)
        else:
            idx = alive_ids.index(player_id)
            n = len(alive_ids)
            alive_ids_with_target = alive_ids

        left = self.get_player(alive_ids_with_target[(idx - 1) % n])
        right = self.get_player(alive_ids_with_target[(idx + 1) % n])
        return left, right

    def next_turn(self) -> int:
        self.turn_counter += 1
        return self.turn_counter

    def add_log(
        self,
        player_id: str,
        phase: str,
        observation: Dict[str, Any] | None = None,
        thinking: str = "",
        action: Dict[str, Any] | None = None,
        result: Dict[str, Any] | None = None,
    ) -> None:
        self.game_log.append(
            LogEntry(
                turn=self.next_turn(),
                phase=phase,
                player_id=player_id,
                observation=observation or {},
                thinking=thinking,
                action=action or {},
                result=result,
            )
        )
