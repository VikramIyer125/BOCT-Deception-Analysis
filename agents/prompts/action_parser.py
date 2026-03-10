from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from botc.utils import NumberedTargets

logger = logging.getLogger(__name__)

FUZZY_THRESHOLD = 0.6


@dataclass
class AgentResponse:
    condensed_memory: str = ""
    thinking_process: str = ""
    action: str = ""
    raw_response: str = ""
    parse_success: bool = False


_SECTION_PATTERNS = {
    "condensed_memory": r"\[Condensed Memory\]\s*(.*?)(?=\[Thinking Process\]|\[Action\]|$)",
    "thinking_process": r"\[Thinking Process\]\s*(.*?)(?=\[Action\]|$)",
    "action": r"\[Action\]\s*(.*?)$",
}


def parse_agent_response(response_text: str) -> AgentResponse:
    extracted: dict[str, str] = {}
    for key, pattern in _SECTION_PATTERNS.items():
        match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
        extracted[key] = match.group(1).strip() if match else ""

    return AgentResponse(
        condensed_memory=extracted["condensed_memory"],
        thinking_process=extracted["thinking_process"],
        action=extracted["action"],
        raw_response=response_text,
        parse_success=all(extracted.values()),
    )


def _strip_rationale(raw: str) -> str:
    """Remove trailing rationale after em-dash, en-dash, or spaced hyphen."""
    raw = re.split(r"\s*[—–]\s*|\s+-\s+", raw, maxsplit=1)[0]
    return raw.strip()


def _clean_name(raw: str) -> str:
    """Strip markdown formatting, punctuation, and extra whitespace from a name."""
    raw = re.sub(r"[*_`#~\[\](){}]", "", raw)
    raw = raw.strip(" \t\n.,!?;:")
    return raw


def _fuzzy_match(raw: str, name_to_id: dict[str, str]) -> str | None:
    """Return the player ID whose name is closest to *raw*, or None."""
    scored = [
        (name, pid, SequenceMatcher(None, raw.lower(), name).ratio())
        for name, pid in name_to_id.items()
    ]
    best_score = max((s for _, _, s in scored), default=0.0)
    if best_score < FUZZY_THRESHOLD:
        return None
    ties = [pid for _, pid, s in scored if s == best_score]
    return random.choice(ties)


def _resolve_target(
    raw: str,
    name_to_id: dict[str, str],
    numbered_targets: Optional["NumberedTargets"] = None,
) -> str | None:
    """Resolve raw text to player ID. Tries number, exact name, then fuzzy."""
    raw = _clean_name(_strip_rationale(raw).strip("\"'"))
    if numbered_targets and raw.isdigit():
        idx = int(raw)
        if idx in numbered_targets.id_map:
            return numbered_targets.id_map[idx]
    if raw.lower() in name_to_id:
        return name_to_id[raw.lower()]

    fuzzy = _fuzzy_match(raw, name_to_id)
    if fuzzy is not None:
        logger.warning("Fuzzy-matched %r -> player %s", raw, fuzzy)
        return fuzzy

    logger.error("Could not resolve target %r to any player", raw)
    return None


def parse_night_action(
    action_text: str,
    game_state: "object" = None,
    numbered_targets: Optional["NumberedTargets"] = None,
) -> dict:
    """Extract structured data from the [Action] section for night actions."""
    action_text = action_text.strip()
    result: dict = {}

    name_to_id: dict[str, str] = {}
    if game_state is not None and hasattr(game_state, "players"):
        for p in game_state.players:  # type: ignore[attr-defined]
            name_to_id[p.name.lower()] = p.id

    def _resolve(raw: str) -> str | None:
        return _resolve_target(raw, name_to_id, numbered_targets)

    patterns = [
        (r"(?:KILL|POISON|MONK|RAVENKEEPER):\s*(.+)", "target"),
        (r"FORTUNE_TELLER:\s*(.+)", "ft_targets"),
        (r"NOMINATE:\s*(.+)", "nominate"),
        (r"SLAY:\s*(.+)", "slay_target"),
        (r"(?:VOTE|YES|NO)", "vote"),
    ]

    for pattern, key in patterns:
        m = re.search(pattern, action_text, re.IGNORECASE)
        if m:
            if key == "ft_targets":
                parts = re.split(r"[,&]+", m.group(1))
                resolved = [_resolve(p) for p in parts[:2]]
                result["targets"] = [r for r in resolved if r is not None]
            elif key == "vote":
                text_upper = action_text.upper()
                result["vote"] = "YES" in text_upper
            elif key in ("target", "nominate", "slay_target"):
                result[key] = _resolve(m.group(1))
            break

    if not result:
        if "YES" in action_text.upper():
            result["vote"] = True
        elif "NO" in action_text.upper():
            result["vote"] = False
        elif "PASS" in action_text.upper():
            pass

    return result


def parse_day_action(
    action_text: str,
    game_state: "object" = None,
    numbered_targets: Optional["NumberedTargets"] = None,
) -> dict:
    """Extract structured data from the [Action] section for day actions."""
    result: dict = {}

    name_to_id: dict[str, str] = {}
    if game_state is not None and hasattr(game_state, "players"):
        for p in game_state.players:  # type: ignore[attr-defined]
            name_to_id[p.name.lower()] = p.id

    def _resolve(raw: str) -> str | None:
        return _resolve_target(raw, name_to_id, numbered_targets)

    slay_match = re.search(r"SLAY:\s*(.+)", action_text, re.IGNORECASE)
    if slay_match:
        result["slay_target"] = _resolve(slay_match.group(1).split("\n")[0])

    nom_match = re.search(r"NOMINATE:\s*(.+)", action_text, re.IGNORECASE)
    if nom_match:
        result["nominate"] = _resolve(nom_match.group(1).split("\n")[0])

    vote_match = re.search(r"\b(YES|NO)\b", action_text, re.IGNORECASE)
    if vote_match:
        result["vote"] = vote_match.group(1).upper() == "YES"
    else:
        numeric_vote = re.search(r"VOTE:\s*([12])", action_text, re.IGNORECASE)
        if numeric_vote:
            result["vote"] = numeric_vote.group(1) == "1"

    speak_match = re.search(r"SPEAK:\s*(.+)", action_text, re.DOTALL | re.IGNORECASE)
    if speak_match:
        result["speech"] = speak_match.group(1).strip()
    elif not result:
        result["speech"] = action_text.strip()

    return result
