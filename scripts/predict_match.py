from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.prediction_service import PredictionService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict an international football match.")
    parser.add_argument("team_a", help="First team, from this team's perspective.")
    parser.add_argument("team_b", help="Second team.")
    parser.add_argument("--date", default=None, help="Match date in YYYY-MM-DD format.")
    parser.add_argument(
        "--neutral",
        type=int,
        choices=[0, 1],
        default=1,
        help="Whether the match is played on neutral ground.",
    )
    parser.add_argument(
        "--team-a-home",
        type=int,
        choices=[0, 1],
        default=0,
        help="Whether team_a is the home team.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = PredictionService()
    prediction = service.predict_match(
        args.team_a,
        args.team_b,
        match_date=args.date,
        neutral=args.neutral,
        team_a_is_home=args.team_a_home,
    )
    print(json.dumps(prediction, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
