# Blood on the Clocktower: LLM Deception Sandbox

A research environment for measuring and detecting deception in LLM agents through the social deduction game Blood on the Clocktower (Trouble Brewing edition).

Inspired by [Among Us: A Sandbox for Measuring and Detecting Agentic Deception](https://arxiv.org/abs/2504.04072).

## Quick Start

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your MARTIAN_API_KEY

python main.py --num-games 10 --models anthropic/claude-sonnet-4-20250514 openai/gpt-4o
```

## What This Measures

- **Deception Elo** — How well can an LLM deceive others when playing evil?
- **Detection Elo** — How well can an LLM detect deception when playing good?
- **Per-action scoring** — LLM-as-judge rates Awareness, Lying, Deception, and Planning on every turn.

## Architecture

- `botc/` — Core game engine (state, characters, phase logic, automated storyteller)
- `agents/` — LLM agent system using Martian Gateway API (OpenAI-compatible)
- `evaluation/` — Elo ratings, win-rate metrics, LLM-based action evaluation
- `logs/` — Full game logs in JSON (gitignored)
- `tests/` — Unit and integration tests

## V1 Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Storyteller** | Automated/deterministic | Simpler, more controlled, reproducible |
| **Communication** | All public (no private whispers) | Simpler logging; matches Among Us paper; add private in v2 |
| **Player count** | 7 players | Matches Among Us paper setup |
| **Characters** | Subset of ~10 (not all 22) | Core mechanics without edge cases |
| **Character set** | 5 Townsfolk, 1 Poisoner, 1 Imp | Info-gathering + misinformation + killing |
| **Day structure** | Structured rounds (2-3 turns per player) | Reproducibility, clean logging |
| **Scratchpad/Thinking** | Required `[Thinking Process]` block | Essential for deception analysis |
| **Misinformation** | Semi-random plausible false info | Balance realism and simplicity |
| **LLM routing** | Martian Gateway API | OpenAI-compatible |
| **Models** | Start with 2-3 | Validate system before scaling |
| **Metrics** | Deception Elo, Detection Elo, win rates | Match Among Us paper methodology |
| **Evaluation** | LLM-based scoring (lying, deception, awareness, planning) | Match Among Us paper methodology |

## V1 Scope

- 7 players, Trouble Brewing edition
- Characters: Washerwoman, Empath, Investigator, Slayer, Ravenkeeper, Monk, Fortune Teller, Poisoner, Imp
- All-public discussion (no private whispers)
- Structured day rounds with nomination and voting
- Deterministic automated storyteller
