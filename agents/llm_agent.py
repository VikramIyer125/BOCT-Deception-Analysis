from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from agents.base_agent import BaseAgent
from agents.martian_client import MartianClient
from agents.prompts.action_parser import (
    AgentResponse,
    parse_agent_response,
    parse_day_action,
    parse_night_action,
)
from agents.prompts.observation import build_user_prompt
from agents.prompts.system_prompts import build_system_prompt

if TYPE_CHECKING:
    from botc.game_state import GameState

logger = logging.getLogger(__name__)

_TARGET_KEYS = ("target", "nominate", "slay_target")


def _has_unresolved_target(fields: Dict[str, Any]) -> bool:
    """True if any target field was matched but resolved to None."""
    return any(k in fields and fields[k] is None for k in _TARGET_KEYS)


def _build_retry_prompt(numbered_targets: Any, available_actions: List[str]) -> str:
    target_list = ""
    if numbered_targets is not None:
        target_list = f"\n{numbered_targets.prompt_lines}\n"
    actions = "\n".join(available_actions) if available_actions else ""
    return (
        "Your previous response could not be parsed into a valid action. "
        "You MUST respond with ONLY the action keyword followed by a NUMBER "
        "from the list below. Do NOT include anything else.\n\n"
        f"Available actions:\n{actions}\n"
        f"Players:{target_list}\n"
        "Respond with ONLY the action and number, e.g.: KILL: 3"
    )


class LLMAgent(BaseAgent):
    """Agent that uses the Martian Gateway to get LLM completions."""

    def __init__(self, player_id: str, model: str, client: MartianClient | None = None):
        super().__init__(player_id)
        self.model = model
        self.client = client or MartianClient(model=model)

    def _parse_action(
        self, action_text: str, action_context: str, game_state: "GameState", numbered_targets: Any,
    ) -> Dict[str, Any]:
        if "night" in action_context.lower():
            return parse_night_action(action_text, game_state, numbered_targets)
        return parse_day_action(action_text, game_state, numbered_targets)

    def act(
        self,
        game_state: "GameState",
        action_context: str,
        available_actions: List[str],
        numbered_targets: Any = None,
    ) -> Dict[str, Any]:
        player = game_state.get_player(self.player_id)

        system_prompt = build_system_prompt(game_state, player)
        user_prompt = build_user_prompt(
            game_state,
            player,
            action_context,
            available_actions,
            condensed_memory=self.condensed_memory,
        )

        raw_response = self.client.get_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        parsed: AgentResponse = parse_agent_response(raw_response)

        if parsed.condensed_memory:
            self.condensed_memory = parsed.condensed_memory

        action_fields = self._parse_action(
            parsed.action, action_context, game_state, numbered_targets,
        )

        if _has_unresolved_target(action_fields) and numbered_targets is not None:
            logger.warning(
                "Player %s (%s): unresolved target, retrying with strict prompt",
                player.name, self.model,
            )
            retry_prompt = _build_retry_prompt(numbered_targets, available_actions)
            try:
                retry_raw = self.client.get_completion(
                    system_prompt=system_prompt,
                    user_prompt=retry_prompt,
                )
                retry_parsed = parse_agent_response(retry_raw)
                retry_fields = self._parse_action(
                    retry_parsed.action or retry_raw,
                    action_context, game_state, numbered_targets,
                )
                if not _has_unresolved_target(retry_fields):
                    action_fields = retry_fields
                    logger.info("Retry succeeded for player %s", player.name)
                else:
                    logger.error(
                        "Retry also failed for player %s (%s): %r",
                        player.name, self.model, retry_raw[:200],
                    )
            except Exception:
                logger.error(
                    "Retry API call failed for player %s (%s)",
                    player.name, self.model, exc_info=True,
                )

        game_state.add_log(
            player_id=self.player_id,
            phase=action_context,
            observation={"prompt_preview": user_prompt[:500]},
            thinking=parsed.thinking_process,
            action={"raw": parsed.action, **action_fields},
        )

        return {
            "thinking": parsed.thinking_process,
            "action_text": parsed.action,
            "condensed_memory": parsed.condensed_memory,
            "parse_success": parsed.parse_success,
            **action_fields,
        }
