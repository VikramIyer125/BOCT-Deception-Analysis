from __future__ import annotations

import re
from dataclasses import dataclass, field


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


def parse_night_action(action_text: str, game_state: "object" = None) -> dict:
    """Extract structured data from the [Action] section for night actions."""
    action_text = action_text.strip()
    result: dict = {}

    name_to_id: dict[str, str] = {}
    if game_state is not None and hasattr(game_state, "players"):
        for p in game_state.players:  # type: ignore[attr-defined]
            name_to_id[p.name.lower()] = p.id

    def _resolve(raw: str) -> str:
        raw = _strip_rationale(raw).strip("\"'")
        if raw.lower() in name_to_id:
            return name_to_id[raw.lower()]
        return raw

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
                result["targets"] = [_resolve(p) for p in parts[:2]]
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


def parse_day_action(action_text: str, game_state: "object" = None) -> dict:
    """Extract structured data from the [Action] section for day actions."""
    result: dict = {}

    name_to_id: dict[str, str] = {}
    if game_state is not None and hasattr(game_state, "players"):
        for p in game_state.players:  # type: ignore[attr-defined]
            name_to_id[p.name.lower()] = p.id

    def _resolve(raw: str) -> str:
        raw = _strip_rationale(raw).strip("\"'")
        if raw.lower() in name_to_id:
            return name_to_id[raw.lower()]
        return raw

    slay_match = re.search(r"SLAY:\s*(.+)", action_text, re.IGNORECASE)
    if slay_match:
        result["slay_target"] = _resolve(slay_match.group(1).split("\n")[0])

    nom_match = re.search(r"NOMINATE:\s*(.+)", action_text, re.IGNORECASE)
    if nom_match:
        result["nominate"] = _resolve(nom_match.group(1).split("\n")[0])

    vote_match = re.search(r"\b(YES|NO)\b", action_text, re.IGNORECASE)
    if vote_match:
        result["vote"] = vote_match.group(1).upper() == "YES"

    speak_match = re.search(r"SPEAK:\s*(.+)", action_text, re.DOTALL | re.IGNORECASE)
    if speak_match:
        result["speech"] = speak_match.group(1).strip()
    elif not result:
        result["speech"] = action_text.strip()

    return result
