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


class LLMAgent(BaseAgent):
    """Agent that uses the Martian Gateway to get LLM completions."""

    def __init__(self, player_id: str, model: str, client: MartianClient | None = None):
        super().__init__(player_id)
        self.model = model
        self.client = client or MartianClient(model=model)

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

        if "night" in action_context.lower():
            action_fields = parse_night_action(
                parsed.action, game_state, numbered_targets
            )
        else:
            action_fields = parse_day_action(
                parsed.action, game_state, numbered_targets
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
