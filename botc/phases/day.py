"""Day phase — discussion rounds, nominations, voting, execution."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

from botc.characters import CHARACTER_REGISTRY
from botc.characters.townsfolk import Slayer
from botc.game_state import Message, Nomination
from botc.utils import NumberedTargets

if TYPE_CHECKING:
    from botc.game_state import GameState


def run_day_phase(
    game_state: "GameState",
    get_agent_action: Callable,
    discussion_rounds: int = 2,
) -> "GameState":
    """Run a complete day phase: discussion, nominations, voting, execution."""

    game_state.phase = "day"
    game_state.nominations = []
    game_state.executed_today = None
    game_state.discussion_transcript = []

    # ── Discussion rounds ────────────────────────────────────────
    for round_num in range(discussion_rounds):
        for player in game_state.all_players_in_seating_order():
            if not player.alive:
                continue

            day_actions, day_numbered = _get_day_actions(game_state, player)
            action_lines = ["SPEAK: <your message to the group>"]
            action_lines.extend(day_actions)

            action_dict = get_agent_action(
                player.id,
                game_state,
                f"day_{game_state.day_number}_discussion_round_{round_num + 1}",
                action_lines,
                day_numbered,
            )

            speech = action_dict.get("speech", "")
            if speech:
                game_state.discussion_transcript.append(
                    Message(
                        player_id=player.id,
                        content=speech,
                        phase=f"day_{game_state.day_number}_round_{round_num + 1}",
                        timestamp=game_state.turn_counter,
                    )
                )

            slay_target = action_dict.get("slay_target")
            if slay_target and game_state.get_player_safe(slay_target) is not None:
                game_state = _resolve_slay(game_state, player, slay_target)

    # ── Dead player speeches (one statement each) ────────────────
    for player in game_state.all_players_in_seating_order():
        if player.alive:
            continue
        action_dict = get_agent_action(
            player.id,
            game_state,
            f"day_{game_state.day_number}_dead_speech",
            ["SPEAK: <your message to the group> (you are dead but may still speak)"],
            None,
        )
        speech = action_dict.get("speech", "")
        if speech:
            game_state.discussion_transcript.append(
                Message(
                    player_id=player.id,
                    content=speech,
                    phase=f"day_{game_state.day_number}_dead_speech",
                    timestamp=game_state.turn_counter,
                )
            )

    # ── Nomination phase ─────────────────────────────────────────
    game_state = _run_nominations(game_state, get_agent_action)

    # ── Voting phase ─────────────────────────────────────────────
    game_state = _run_voting(game_state, get_agent_action)

    # ── Execution ────────────────────────────────────────────────
    game_state = _resolve_execution(game_state)

    return game_state


# ── Nomination ───────────────────────────────────────────────────


def _run_nominations(
    game_state: "GameState",
    get_agent_action: Callable,
) -> "GameState":
    """Each living player gets one chance to nominate."""
    nominators_used: set[str] = set()
    nominees_used: set[str] = set()

    for player in game_state.living_players_in_seating_order():
        if player.id in nominators_used:
            continue

        eligible = [
            p for p in game_state.players
            if p.alive and p.id != player.id and p.id not in nominees_used
        ]
        if not eligible:
            continue

        numbered = NumberedTargets.from_players(eligible)
        action_dict = get_agent_action(
            player.id,
            game_state,
            f"day_{game_state.day_number}_nomination",
            [
                "NOMINATE: <number> — Nominate a player for execution.",
                "PASS — Do not nominate anyone.",
                "ELIGIBLE PLAYERS (use ONLY these numbers, they change each turn):",
                f"{numbered.prompt_lines}",
            ],
            numbered,
        )

        nominee_id = action_dict.get("nominate")
        if (
            nominee_id
            and nominee_id not in nominees_used
            and game_state.get_player_safe(nominee_id) is not None
        ):
            nom = Nomination(
                id=str(uuid.uuid4()),
                nominator_id=player.id,
                nominee_id=nominee_id,
            )
            game_state.nominations.append(nom)
            nominators_used.add(player.id)
            nominees_used.add(nominee_id)

    return game_state


# ── Voting ───────────────────────────────────────────────────────


def _run_voting(
    game_state: "GameState",
    get_agent_action: Callable,
) -> "GameState":
    """For each nomination, all eligible players vote."""
    for nom in game_state.nominations:
        nominator = game_state.get_player(nom.nominator_id)
        nominee = game_state.get_player(nom.nominee_id)

        for voter in game_state.all_players_in_seating_order():
            can_vote = voter.alive or (not voter.alive and not voter.ghost_vote_used)
            if not can_vote:
                continue

            vote_actions = [
                f"VOTE on {nominator.name}'s nomination of {nominee.name}.",
                "YES — Vote to execute.",
                "NO — Vote against execution.",
            ]
            if not voter.alive:
                vote_actions.insert(0,
                    "You are DEAD but you still have your ONE ghost vote. "
                    "You MUST vote YES or NO."
                )

            action_dict = get_agent_action(
                voter.id,
                game_state,
                f"day_{game_state.day_number}_vote",
                vote_actions,
                None,
            )

            vote = action_dict.get("vote", False)
            if vote:
                nom.votes_for.append(voter.id)
            else:
                nom.votes_against.append(voter.id)

            if not voter.alive and vote:
                voter.ghost_vote_used = True

        nom.resolved = True

    return game_state


# ── Execution resolution ─────────────────────────────────────────


def _resolve_execution(game_state: "GameState") -> "GameState":
    """Execute the player with the most votes (if >= 50% of living)."""
    if not game_state.nominations:
        return game_state

    living_count = len(game_state.living_players())
    threshold = living_count / 2

    best_nom: Optional[Nomination] = None
    best_votes = 0

    for nom in game_state.nominations:
        v = len(nom.votes_for)
        if v > best_votes:
            best_votes = v
            best_nom = nom

    if best_nom and best_votes >= threshold:
        target = game_state.get_player(best_nom.nominee_id)
        target.alive = False
        game_state.executed_today = target.id

    return game_state


# ── Slayer resolution ────────────────────────────────────────────


def _resolve_slay(
    game_state: "GameState",
    slayer_player: "Player",
    target_id: str,
) -> "GameState":
    from botc.game_state import Player

    char_cls = CHARACTER_REGISTRY.get(slayer_player.character_name)
    if char_cls is None or char_cls.name != "Slayer":
        return game_state
    char = Slayer()
    game_state, died = char.resolve_slay(game_state, slayer_player, target_id)
    if died:
        game_state.discussion_transcript.append(
            Message(
                player_id="storyteller",
                content=f"{slayer_player.name} used the Slayer ability on {game_state.get_player(target_id).name}. They were the Demon! They die!",
                phase=f"day_{game_state.day_number}_slay",
                timestamp=game_state.turn_counter,
            )
        )
    else:
        game_state.discussion_transcript.append(
            Message(
                player_id="storyteller",
                content=f"{slayer_player.name} used the Slayer ability on {game_state.get_player(target_id).name}. Nothing happens.",
                phase=f"day_{game_state.day_number}_slay",
                timestamp=game_state.turn_counter,
            )
        )
    return game_state


# ── Helpers ──────────────────────────────────────────────────────


def _get_day_actions(game_state: "GameState", player: "Player") -> tuple[list[str], Optional[NumberedTargets]]:
    from botc.game_state import Player

    char_cls = CHARACTER_REGISTRY.get(player.character_name)
    if char_cls is None:
        return [], None
    char = char_cls()
    return char.get_day_actions(game_state, player)
