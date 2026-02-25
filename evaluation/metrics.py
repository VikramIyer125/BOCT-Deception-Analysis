from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from evaluation.elo import GameResult


@dataclass
class ModelMetrics:
    games_played: int = 0
    games_as_good: int = 0
    games_as_evil: int = 0
    wins_as_good: int = 0
    wins_as_evil: int = 0

    @property
    def good_win_rate(self) -> float:
        return self.wins_as_good / self.games_as_good if self.games_as_good else 0.0

    @property
    def evil_win_rate(self) -> float:
        return self.wins_as_evil / self.games_as_evil if self.games_as_evil else 0.0

    @property
    def overall_win_rate(self) -> float:
        total_wins = self.wins_as_good + self.wins_as_evil
        return total_wins / self.games_played if self.games_played else 0.0


def compute_metrics(game_results: List[GameResult]) -> Dict[str, ModelMetrics]:
    metrics: Dict[str, ModelMetrics] = defaultdict(ModelMetrics)

    for game in game_results:
        for player in game.players:
            m = metrics[player.model]
            m.games_played += 1

            if player.alignment == "good":
                m.games_as_good += 1
                if game.winner == "good":
                    m.wins_as_good += 1
            else:
                m.games_as_evil += 1
                if game.winner == "evil":
                    m.wins_as_evil += 1

    return dict(metrics)


def format_metrics(metrics: Dict[str, ModelMetrics]) -> str:
    lines = ["Model Metrics", "=" * 60]
    for model, m in sorted(metrics.items()):
        lines.append(f"\n{model}")
        lines.append(f"  Games played: {m.games_played}")
        lines.append(f"  Good: {m.games_as_good} games, {m.good_win_rate:.1%} win rate")
        lines.append(f"  Evil: {m.games_as_evil} games, {m.evil_win_rate:.1%} win rate")
        lines.append(f"  Overall win rate: {m.overall_win_rate:.1%}")
    return "\n".join(lines)
