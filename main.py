#!/usr/bin/env python3
"""Entry point — run BOTC games with LLM agents and compute Elo ratings."""

from __future__ import annotations

import argparse
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()

from config import DEFAULT_MODELS, GameConfig, ModelConfig
from botc.game_state import GameState
from botc.setup import setup_game
from botc.phases.night import run_first_night, run_night_phase
from botc.phases.day import run_day_phase
from botc.phases.storyteller import announce_deaths, check_win_conditions
from agents.llm_agent import LLMAgent
from agents.prompts.action_parser import parse_day_action, parse_night_action
from evaluation.elo import calculate_elo_from_games, GameResult, PlayerResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Model-to-player assignment ───────────────────────────────────


def assign_models_to_players(
    num_players: int,
    available_models: List[str],
) -> Dict[str, str]:
    player_ids = [f"p{i}" for i in range(num_players)]
    assignments: Dict[str, str] = {}
    for i, pid in enumerate(player_ids):
        assignments[pid] = available_models[i % len(available_models)]
    return assignments


# ── Orchestration ────────────────────────────────────────────────


def run_game(
    player_models: Dict[str, str],
    config: GameConfig,
    seed: int | None = None,
) -> Dict[str, Any]:
    """Run a complete game and return the serialisable log."""

    if seed is not None:
        random.seed(seed)

    game_state = setup_game(player_models, config)
    agents: Dict[str, LLMAgent] = {
        pid: LLMAgent(pid, model)
        for pid, model in player_models.items()
    }

    def get_agent_action(
        player_id: str,
        gs: GameState,
        context: str,
        available_actions: Any,
    ) -> Dict[str, Any]:
        if isinstance(available_actions, str):
            available_actions = [available_actions]
        return agents[player_id].act(gs, context, available_actions)

    # ── First night ──────────────────────────────────────────────
    logger.info("=== First Night ===")
    game_state = run_first_night(game_state, get_agent_action)
    death_msg = announce_deaths(game_state)
    logger.info(death_msg)

    day_count = 0

    while game_state.winner is None and day_count < config.max_days:
        day_count += 1

        # ── Day ──────────────────────────────────────────────────
        game_state.phase = "day"
        logger.info("=== Day %d ===", day_count)
        game_state = run_day_phase(game_state, get_agent_action, config.discussion_rounds)
        game_state = check_win_conditions(game_state)

        if game_state.executed_today:
            executed = game_state.get_player(game_state.executed_today)
            logger.info("Executed: %s (%s)", executed.name, executed.character_name)

        if game_state.winner:
            break

        # ── Night ────────────────────────────────────────────────
        logger.info("=== Night %d ===", day_count)
        game_state = run_night_phase(game_state, get_agent_action)
        death_msg = announce_deaths(game_state)
        logger.info(death_msg)
        game_state = check_win_conditions(game_state)

    logger.info("=== Game Over — %s wins! ===", game_state.winner or "nobody")

    return _build_game_log(game_state, player_models)


def _build_game_log(
    game_state: GameState,
    player_models: Dict[str, str],
) -> Dict[str, Any]:
    return {
        "winner": game_state.winner,
        "day_number": game_state.day_number,
        "players": [
            {
                "id": p.id,
                "name": p.name,
                "character": p.character_name,
                "alignment": p.alignment,
                "alive": p.alive,
                "model": player_models.get(p.id, "unknown"),
            }
            for p in game_state.players
        ],
        "log": [entry.model_dump() for entry in game_state.game_log],
    }


def _to_game_result(game_log: Dict[str, Any]) -> GameResult:
    return GameResult(
        winner=game_log["winner"] or "none",
        players=[
            PlayerResult(
                player_id=p["id"],
                model=p["model"],
                alignment=p["alignment"],
                character=p["character"],
            )
            for p in game_log["players"]
        ],
    )


# ── CLI ──────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Run BOTC games with LLM agents")
    parser.add_argument("--num-games", type=int, default=10)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--output-dir", type=str, default="logs")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--discussion-rounds", type=int, default=2)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    game_config = GameConfig(seed=args.seed, discussion_rounds=args.discussion_rounds)
    model_config = ModelConfig(available_models=args.models)

    results: List[Dict[str, Any]] = []

    for i in range(args.num_games):
        logger.info("Running game %d/%d ...", i + 1, args.num_games)

        player_models = assign_models_to_players(
            game_config.num_players, model_config.available_models
        )

        game_log = run_game(
            player_models=player_models,
            config=game_config,
            seed=(args.seed + i) if args.seed else None,
        )

        log_path = output_dir / f"game_{i:04d}_{datetime.now().strftime('%Y%m%dT%H%M%S')}.json"
        with open(log_path, "w") as f:
            json.dump(game_log, f, indent=2, default=str)
        logger.info("  Saved log to %s", log_path)

        results.append(game_log)
        logger.info("  Winner: %s", game_log["winner"])

    game_results = [_to_game_result(r) for r in results]
    elo = calculate_elo_from_games(game_results)

    print("\n=== Results ===")
    print("\nDeception Elo (Evil Play):")
    for model, rating in sorted(elo.deception_elo.items(), key=lambda x: -x[1]):
        print(f"  {model}: {rating:.1f}")

    print("\nDetection Elo (Good Play):")
    for model, rating in sorted(elo.detection_elo.items(), key=lambda x: -x[1]):
        print(f"  {model}: {rating:.1f}")


if __name__ == "__main__":
    main()
