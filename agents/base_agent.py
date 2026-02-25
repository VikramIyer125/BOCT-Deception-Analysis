from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from botc.game_state import GameState


class BaseAgent(ABC):
    """Abstract base for all agents (LLM or human)."""

    def __init__(self, player_id: str):
        self.player_id = player_id
        self.condensed_memory: str = ""

    @abstractmethod
    def act(
        self,
        game_state: "GameState",
        action_context: str,
        available_actions: List[str],
    ) -> Dict[str, Any]:
        """Return a dict with at least 'thinking', 'action_text', and parsed fields."""
        ...
