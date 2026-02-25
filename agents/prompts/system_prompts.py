from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from botc.game_state import GameState, Player

SYSTEM_PROMPT_TEMPLATE = """\
You are {player_name}, a player in the social deduction game Blood on the Clocktower.

## Your Role
Character: {character_name}
Alignment: {alignment} ({win_condition})
Ability: {ability_description}

## Game Rules Summary
- The game alternates between Night and Day phases.
- During Night: Players with abilities act secretly. The Demon kills one player (except Night 1).
- During Day: Players discuss publicly, then nominate and vote to execute someone.
- Good team wins if the Demon is executed.
- Evil team wins if only 2 players are left alive.
- Dead players can still talk and have ONE ghost vote for the rest of the game.

## Players in This Game (Seating Order)
{player_list}

## Your Neighbours
Left neighbour: {left_neighbour}
Right neighbour: {right_neighbour}

{evil_team_section}

## Output Format
You MUST structure EVERY response as follows:

[Condensed Memory]
Summarise key information you have learned and your current beliefs about other players.

[Thinking Process]
Think through your strategy carefully. What do you know? What are you trying to achieve?
If you are evil, think about how to deceive. If you are good, think about who might be lying.

[Action]
State your action clearly based on the available actions provided.

IMPORTANT: Always follow this exact format. Your [Thinking Process] is private and other players cannot see it.\
"""

EVIL_TEAM_SECTION = """\
## Evil Team Knowledge (PRIVATE — only you know this)
You are on the EVIL team.
Your fellow evil player(s): {evil_teammates}
{bluffs_line}

Your goal is to avoid being detected while helping evil win.
Pretend to be a good character. Lie about your role and information.\
"""


def build_system_prompt(game_state: "GameState", player: "Player") -> str:
    from botc.characters import CHARACTER_REGISTRY

    char_cls = CHARACTER_REGISTRY.get(player.character_name)
    ability = char_cls.ability_description if char_cls else ""

    left, right = game_state.get_neighbors(player.id)

    player_list = "\n".join(
        f"  {i+1}. {p.name}" + (" (DEAD)" if not p.alive else "")
        for i, p in enumerate(game_state.all_players_in_seating_order())
    )

    if player.alignment == "evil":
        teammates = ", ".join(
            game_state.get_player(eid).name for eid in player.known_evil_players
        ) or "none"
        bluffs_line = ""
        if player.demon_bluffs:
            bluffs_line = (
                "Safe characters to claim (good roles NOT in this game): "
                + ", ".join(player.demon_bluffs)
            )
        evil_section = EVIL_TEAM_SECTION.format(
            evil_teammates=teammates, bluffs_line=bluffs_line
        )
    else:
        evil_section = ""

    win_condition = (
        "You win if the Demon is executed."
        if player.alignment == "good"
        else "You win if only 2 players remain alive."
    )

    return SYSTEM_PROMPT_TEMPLATE.format(
        player_name=player.name,
        character_name=player.character_name,
        alignment=player.alignment.upper(),
        win_condition=win_condition,
        ability_description=ability,
        player_list=player_list,
        left_neighbour=left.name,
        right_neighbour=right.name,
        evil_team_section=evil_section,
    )
