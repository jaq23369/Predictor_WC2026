from __future__ import annotations

import csv
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.prediction_service import PredictionService  # noqa: E402


FIXTURES_PATH = ROOT_DIR / "data" / "processed" / "world_cup_2026_fixtures.csv"
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "world_cup_2026_predictions.csv"

FIELDNAMES = [
    "date",
    "home_team",
    "away_team",
    "city",
    "country",
    "neutral",
    "predicted_winner",
    "home_win_probability",
    "draw_probability",
    "away_win_probability",
    "home_expected_goals",
    "away_expected_goals",
    "most_likely_score",
    "most_likely_score_probability",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    service = PredictionService()
    output_rows: list[dict[str, object]] = []

    for fixture in read_csv(FIXTURES_PATH):
        neutral = int(fixture["neutral"])
        prediction = service.predict_match(
            fixture["home_team"],
            fixture["away_team"],
            match_date=fixture["date"],
            neutral=neutral,
            team_a_is_home=0 if neutral else 1,
        )
        top_scoreline = prediction["top_scorelines"][0]
        output_rows.append(
            {
                "date": fixture["date"],
                "home_team": fixture["home_team"],
                "away_team": fixture["away_team"],
                "city": fixture["city"],
                "country": fixture["country"],
                "neutral": neutral,
                "predicted_winner": prediction["winner"],
                "home_win_probability": prediction["probabilities"]["team_a_win"],
                "draw_probability": prediction["probabilities"]["draw"],
                "away_win_probability": prediction["probabilities"]["team_b_win"],
                "home_expected_goals": prediction["expected_goals"]["team_a"],
                "away_expected_goals": prediction["expected_goals"]["team_b"],
                "most_likely_score": top_scoreline["score"],
                "most_likely_score_probability": top_scoreline["probability"],
            }
        )

    write_csv(OUTPUT_PATH, output_rows)
    print(f"saved={OUTPUT_PATH}")
    print(f"rows={len(output_rows)}")


if __name__ == "__main__":
    main()
