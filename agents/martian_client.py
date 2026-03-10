from __future__ import annotations

import os
import time
import logging
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


class MartianClient:
    """Thin wrapper around the Martian Gateway (OpenAI-compatible) API."""

    def __init__(
        self,
        model: str = "anthropic/claude-sonnet-4-20250514",
        base_url: str = "https://api.withmartian.com/v1",
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        api_key = os.getenv("MARTIAN_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "MARTIAN_API_KEY not set. Copy .env.example to .env and add your key."
            )
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    _MAX_COMPLETION_TOKENS_MODELS = ("openai/gpt-5", "openai/o3", "openai/o4")

    def _uses_max_completion_tokens(self) -> bool:
        return any(self.model.startswith(p) for p in self._MAX_COMPLETION_TOKENS_MODELS)

    def get_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        for attempt in range(self.max_retries):
            try:
                token_param = (
                    {"max_completion_tokens": max_tokens}
                    if self._uses_max_completion_tokens()
                    else {"max_tokens": max_tokens}
                )
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    **token_param,
                )
                return response.choices[0].message.content or ""
            except Exception:
                logger.warning(
                    "Martian API call failed (attempt %d/%d)",
                    attempt + 1,
                    self.max_retries,
                    exc_info=True,
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        raise RuntimeError(f"Martian API call failed after {self.max_retries} attempts")
