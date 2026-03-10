from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from botc.game_state import GameState, Player


def build_observation(game_state: "GameState", player: "Player") -> Dict[str, Any]:
    obs: Dict[str, Any] = {
        "phase": game_state.phase,
        "day_number": game_state.day_number,
        "alive_players": [p.name for p in game_state.players if p.alive],
        "dead_players": [p.name for p in game_state.players if not p.alive],
        "your_info_received": [
            {"night": info.night, "result": info.description}
            for info in player.received_info
        ],
    }

    if game_state.phase == "day":
        obs["discussion_so_far"] = [
            {"player": game_state.get_player(m.player_id).name if m.player_id != "storyteller" else "Storyteller",
             "said": m.content}
            for m in game_state.discussion_transcript
        ]
        obs["nominations_today"] = [
            {
                "nominator": nominator.name,
                "nominee": nominee.name,
                "votes_for": len(n.votes_for),
                "votes_against": len(n.votes_against),
                "resolved": n.resolved,
            }
            for n in game_state.nominations
            if (nominator := game_state.get_player_safe(n.nominator_id)) is not None
            and (nominee := game_state.get_player_safe(n.nominee_id)) is not None
        ]
        obs["you_have_nominated_today"] = any(
            n.nominator_id == player.id for n in game_state.nominations
        )

    if game_state.night_deaths:
        obs["deaths_announced"] = [
            game_state.get_player(pid).name for pid in game_state.night_deaths
        ]

    return obs


def build_user_prompt(
    game_state: "GameState",
    player: "Player",
    action_context: str,
    available_actions: List[str],
    condensed_memory: str = "",
) -> str:
    obs = build_observation(game_state, player)

    info_lines = "\n".join(
        f"  Night {i['night']}: {i['result']}" for i in obs["your_info_received"]
    ) or "  (none yet)"

    discussion = ""
    if "discussion_so_far" in obs and obs["discussion_so_far"]:
        discussion = "## Discussion So Far\n" + "\n".join(
            f"  {d['player']}: {d['said']}" for d in obs["discussion_so_far"]
        )

    nominations = ""
    if "nominations_today" in obs and obs["nominations_today"]:
        nominations = "## Nominations Today\n" + "\n".join(
            f"  {n['nominator']} nominated {n['nominee']} "
            f"(votes for: {n['votes_for']}, against: {n['votes_against']})"
            for n in obs["nominations_today"]
        )

    deaths = ""
    if "deaths_announced" in obs and obs["deaths_announced"]:
        deaths = (
            "## Deaths Announced\n  " + ", ".join(obs["deaths_announced"]) + " died."
        )

    memory_block = ""
    if condensed_memory:
        memory_block = f"## Your Previous Memory\n{condensed_memory}\n"

    actions_block = "\n".join(f"  - {a}" for a in available_actions)

    return f"""\
## Current Situation
Phase: {obs['phase'].upper()} (Day {obs['day_number']})
Alive players: {', '.join(obs['alive_players'])}
Dead players: {', '.join(obs['dead_players']) or 'None yet'}

## Information From Your Ability
{info_lines}

{memory_block}
{discussion}

{nominations}

{deaths}

## Action Required: {action_context}

Available actions:
{actions_block}

Remember to respond with [Condensed Memory], [Thinking Process], and [Action].\
"""
