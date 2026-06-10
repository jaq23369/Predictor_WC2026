from __future__ import annotations

import csv
import math
from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[3]
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
ARTIFACTS_DIR = ROOT_DIR / "models" / "artifacts"

MATCHES_PATH = PROCESSED_DIR / "matches_clean.csv"
ELO_PATH = PROCESSED_DIR / "elo_clean.csv"
FIFA_PATH = PROCESSED_DIR / "fifa_rankings_clean.csv"
FIXTURES_PATH = PROCESSED_DIR / "world_cup_2026_fixtures.csv"
PREDICTIONS_PATH = PROCESSED_DIR / "world_cup_2026_predictions.csv"
FOOTBALL_DATA_MATCHES_PATH = PROCESSED_DIR / "football_data_wc_2026_matches.csv"
FOOTBALL_DATA_TEAMS_PATH = PROCESSED_DIR / "football_data_wc_2026_teams.csv"
FOOTBALL_DATA_STANDINGS_PATH = PROCESSED_DIR / "football_data_wc_2026_standings.csv"
TRANSFERMARKT_VALUES_PATH = PROCESSED_DIR / "transfermarkt_national_team_values.csv"
SQUADS_PATH = PROCESSED_DIR / "world_cup_2026_squads_enriched.csv"
SQUAD_SUMMARY_PATH = PROCESSED_DIR / "world_cup_2026_squad_summary.csv"
THESPORTSDB_TEAM_MAPPING_PATH = PROCESSED_DIR / "thesportsdb_team_mapping.csv"
THESPORTSDB_PLAYERS_PATH = PROCESSED_DIR / "thesportsdb_players.csv"
THESPORTSDB_EVENTS_PATH = PROCESSED_DIR / "thesportsdb_events.csv"
THESPORTSDB_RECENT_FORM_PATH = PROCESSED_DIR / "thesportsdb_recent_form.csv"
THESPORTSDB_RECENT_MATCH_STATS_PATH = PROCESSED_DIR / "thesportsdb_recent_match_stats.csv"
THESPORTSDB_COVERAGE_PATH = PROCESSED_DIR / "thesportsdb_coverage.csv"
API_FOOTBALL_TEAM_MAPPING_PATH = PROCESSED_DIR / "api_football_team_mapping.csv"
API_FOOTBALL_FIXTURES_PATH = PROCESSED_DIR / "api_football_fixtures.csv"
API_FOOTBALL_FIXTURE_STATISTICS_PATH = PROCESSED_DIR / "api_football_fixture_statistics.csv"
API_FOOTBALL_TEAM_MATCH_STATS_PATH = PROCESSED_DIR / "api_football_team_match_stats.csv"
API_FOOTBALL_COVERAGE_PATH = PROCESSED_DIR / "api_football_coverage.csv"
CLASSIFICATION_MODEL_PATH = ARTIFACTS_DIR / "classification_model.pkl"
SCORE_MODEL_PATH = ARTIFACTS_DIR / "poisson_score_model.pkl"

TARGET_LABELS = {
    0: "loss",
    1: "draw",
    2: "win",
}

TEAM_ALIASES = {
    "Democratic Republic of Congo": "DR Congo",
    "Democratic Republic of the Congo": "DR Congo",
    "Congo DR": "DR Congo",
    "Zaire": "DR Congo",
    "Zaïre": "DR Congo",
    "USA": "United States",
    "United States of America": "United States",
    "Korea Republic": "South Korea",
    "Republic of Korea": "South Korea",
    "IR Iran": "Iran",
    "Islamic Republic of Iran": "Iran",
    "Ivory Coast": "Côte d'Ivoire",
    "Cote d'Ivoire": "Côte d'Ivoire",
    "Czech Republic": "Czechia",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Cape Verde Islands": "Cape Verde",
    "Cabo Verde": "Cape Verde",
    "Turkiye": "Turkey",
    "Türkiye": "Turkey",
}


def parse_date(value: str | date | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def read_optional_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return read_csv(path)


def normalize_name(value: str) -> str:
    name = " ".join(value.replace("\xa0", " ").split()).strip()
    return TEAM_ALIASES.get(name, name)


def result_for_team(goals_for: int, goals_against: int) -> str:
    if goals_for > goals_against:
        return "win"
    if goals_for == goals_against:
        return "draw"
    return "loss"


def recent_stats(history: list[dict[str, Any]], n: int) -> dict[str, float | int]:
    recent = history[-n:]
    if not recent:
        return {
            f"wins_last_{n}": 0,
            f"draws_last_{n}": 0,
            f"losses_last_{n}": 0,
            f"points_last_{n}": 0,
            f"goals_scored_last_{n}": 0,
            f"goals_conceded_last_{n}": 0,
            f"avg_goals_scored_last_{n}": 0.0,
            f"avg_goals_conceded_last_{n}": 0.0,
            f"clean_sheets_last_{n}": 0,
            f"weighted_form_last_{n}": 0.0,
            f"avg_opponent_elo_last_{n}": 0.0,
            f"wins_vs_top30_last_{n}": 0,
            f"points_vs_top30_last_{n}": 0,
            f"wins_vs_top50_last_{n}": 0,
            f"points_vs_top50_last_{n}": 0,
            f"elo_change_last_{n}": 0.0,
        }

    wins = sum(1 for match in recent if match["result"] == "win")
    draws = sum(1 for match in recent if match["result"] == "draw")
    losses = sum(1 for match in recent if match["result"] == "loss")
    points_by_result = {"win": 3, "draw": 1, "loss": 0}
    points = sum(points_by_result[match["result"]] for match in recent)
    goals_for = sum(int(match["goals_for"]) for match in recent)
    goals_against = sum(int(match["goals_against"]) for match in recent)
    clean_sheets = sum(1 for match in recent if int(match["goals_against"]) == 0)
    weights = list(range(1, len(recent) + 1))
    weighted_points = sum(
        points_by_result[match["result"]] * weight
        for match, weight in zip(recent, weights)
    )
    opponent_elos = [
        float(match["opponent_elo"])
        for match in recent
        if match.get("opponent_elo") not in ("", None)
    ]
    top30_matches = [
        match
        for match in recent
        if match.get("opponent_rank") not in ("", None)
        and float(match["opponent_rank"]) <= 30
    ]
    top50_matches = [
        match
        for match in recent
        if match.get("opponent_rank") not in ("", None)
        and float(match["opponent_rank"]) <= 50
    ]
    elo_values = [
        float(match["team_elo"])
        for match in recent
        if match.get("team_elo") not in ("", None)
    ]
    count = len(recent)

    return {
        f"wins_last_{n}": wins,
        f"draws_last_{n}": draws,
        f"losses_last_{n}": losses,
        f"points_last_{n}": points,
        f"goals_scored_last_{n}": goals_for,
        f"goals_conceded_last_{n}": goals_against,
        f"avg_goals_scored_last_{n}": goals_for / count,
        f"avg_goals_conceded_last_{n}": goals_against / count,
        f"clean_sheets_last_{n}": clean_sheets,
        f"weighted_form_last_{n}": weighted_points / sum(weights),
        f"avg_opponent_elo_last_{n}": sum(opponent_elos) / len(opponent_elos)
        if opponent_elos
        else 0.0,
        f"wins_vs_top30_last_{n}": sum(
            1 for match in top30_matches if match["result"] == "win"
        ),
        f"points_vs_top30_last_{n}": sum(
            points_by_result[match["result"]] for match in top30_matches
        ),
        f"wins_vs_top50_last_{n}": sum(
            1 for match in top50_matches if match["result"] == "win"
        ),
        f"points_vs_top50_last_{n}": sum(
            points_by_result[match["result"]] for match in top50_matches
        ),
        f"elo_change_last_{n}": elo_values[-1] - elo_values[0]
        if len(elo_values) >= 2
        else 0.0,
    }


def build_time_series(
    rows: list[dict[str, str]],
    team_key: str,
    date_key: str,
    value_keys: list[str],
) -> dict[str, dict[str, list[Any]]]:
    series: dict[str, dict[str, list[Any]]] = defaultdict(lambda: {"dates": []})
    for row in rows:
        team = normalize_name(row[team_key])
        row_date = parse_date(row[date_key])
        series[team]["dates"].append(row_date)
        for value_key in value_keys:
            value = row[value_key]
            series[team].setdefault(value_key, []).append(float(value))
    return series


def value_before(
    series: dict[str, dict[str, list[Any]]],
    team: str,
    match_date: date,
    value_key: str,
    strict: bool = True,
) -> float:
    team_series = series.get(team)
    if not team_series:
        raise ValueError(f"No hay datos de {value_key} para {team}")

    dates = team_series["dates"]
    index = bisect_left(dates, match_date) - 1 if strict else bisect_right(dates, match_date) - 1
    if index < 0:
        raise ValueError(f"No hay datos historicos de {value_key} para {team} antes de {match_date}")
    return float(team_series[value_key][index])


def optional_value_before(
    series: dict[str, dict[str, list[Any]]],
    team: str,
    match_date: date,
    value_key: str,
    strict: bool = True,
) -> float | str:
    try:
        return value_before(series, team, match_date, value_key, strict=strict)
    except ValueError:
        return ""


def diff(value_a: float, value_b: float) -> float:
    return value_a - value_b


def poisson_probability(expected_goals: float, goals: int) -> float:
    return math.exp(-expected_goals) * expected_goals**goals / math.factorial(goals)


class PredictionService:
    def __init__(
        self,
        classification_model_path: Path = CLASSIFICATION_MODEL_PATH,
        score_model_path: Path = SCORE_MODEL_PATH,
    ) -> None:
        self.classification_artifact = joblib.load(classification_model_path)
        self.score_artifact = joblib.load(score_model_path)
        self.classification_model = self.classification_artifact["model"]
        self.score_model = self.score_artifact["model"]
        self.feature_columns = self.classification_artifact["feature_columns"]

        self.matches = read_csv(MATCHES_PATH)
        self.elo_series = build_time_series(read_csv(ELO_PATH), "team", "date", ["elo"])
        self.fifa_series = build_time_series(
            read_csv(FIFA_PATH),
            "team",
            "ranking_date",
            ["rank", "total_points"],
        )
        self.team_history = self._build_team_history()

    def _build_team_history(self) -> dict[str, list[dict[str, Any]]]:
        history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for match in self.matches:
            home_team = normalize_name(match["home_team"])
            away_team = normalize_name(match["away_team"])
            home_score = int(match["home_score"])
            away_score = int(match["away_score"])
            match_date = parse_date(match["date"])
            home_elo = optional_value_before(self.elo_series, home_team, match_date, "elo", strict=True)
            away_elo = optional_value_before(self.elo_series, away_team, match_date, "elo", strict=True)
            home_rank = optional_value_before(self.fifa_series, home_team, match_date, "rank", strict=False)
            away_rank = optional_value_before(self.fifa_series, away_team, match_date, "rank", strict=False)

            history[home_team].append(
                {
                    "date": match_date,
                    "goals_for": home_score,
                    "goals_against": away_score,
                    "result": result_for_team(home_score, away_score),
                    "team_elo": home_elo,
                    "opponent_elo": away_elo,
                    "opponent_rank": away_rank,
                }
            )
            history[away_team].append(
                {
                    "date": match_date,
                    "goals_for": away_score,
                    "goals_against": home_score,
                    "result": result_for_team(away_score, home_score),
                    "team_elo": away_elo,
                    "opponent_elo": home_elo,
                    "opponent_rank": home_rank,
                }
            )

        return history

    def available_teams(self) -> list[str]:
        teams = set(self.team_history) | set(self.elo_series) | set(self.fifa_series)
        return sorted(teams)

    def world_cup_2026_fixtures(self) -> list[dict[str, str]]:
        return read_csv(FIXTURES_PATH)

    def world_cup_2026_predictions(self) -> list[dict[str, str]]:
        return read_csv(PREDICTIONS_PATH)

    def football_data_world_cup_matches(self) -> list[dict[str, str]]:
        return read_optional_csv(FOOTBALL_DATA_MATCHES_PATH)

    def football_data_world_cup_teams(self) -> list[dict[str, str]]:
        return read_optional_csv(FOOTBALL_DATA_TEAMS_PATH)

    def football_data_world_cup_standings(self) -> list[dict[str, str]]:
        return read_optional_csv(FOOTBALL_DATA_STANDINGS_PATH)

    def transfermarkt_national_team_values(self) -> list[dict[str, str]]:
        return read_optional_csv(TRANSFERMARKT_VALUES_PATH)

    def world_cup_2026_squads(self) -> list[dict[str, str]]:
        return read_optional_csv(SQUADS_PATH)

    def world_cup_2026_squad_summary(self) -> list[dict[str, str]]:
        return read_optional_csv(SQUAD_SUMMARY_PATH)

    def thesportsdb_team_mapping(self) -> list[dict[str, str]]:
        return read_optional_csv(THESPORTSDB_TEAM_MAPPING_PATH)

    def thesportsdb_players(self) -> list[dict[str, str]]:
        return read_optional_csv(THESPORTSDB_PLAYERS_PATH)

    def thesportsdb_events(self) -> list[dict[str, str]]:
        return read_optional_csv(THESPORTSDB_EVENTS_PATH)

    def thesportsdb_recent_form(self) -> list[dict[str, str]]:
        return read_optional_csv(THESPORTSDB_RECENT_FORM_PATH)

    def thesportsdb_recent_match_stats(self) -> list[dict[str, str]]:
        return read_optional_csv(THESPORTSDB_RECENT_MATCH_STATS_PATH)

    def thesportsdb_coverage(self) -> list[dict[str, str]]:
        return read_optional_csv(THESPORTSDB_COVERAGE_PATH)

    def api_football_team_mapping(self) -> list[dict[str, str]]:
        return read_optional_csv(API_FOOTBALL_TEAM_MAPPING_PATH)

    def api_football_fixtures(self) -> list[dict[str, str]]:
        return read_optional_csv(API_FOOTBALL_FIXTURES_PATH)

    def api_football_fixture_statistics(self) -> list[dict[str, str]]:
        return read_optional_csv(API_FOOTBALL_FIXTURE_STATISTICS_PATH)

    def api_football_team_match_stats(self) -> list[dict[str, str]]:
        return read_optional_csv(API_FOOTBALL_TEAM_MATCH_STATS_PATH)

    def api_football_coverage(self) -> list[dict[str, str]]:
        return read_optional_csv(API_FOOTBALL_COVERAGE_PATH)

    def world_cup_2026_simulation(self) -> dict[str, Any]:
        predictions = self.world_cup_2026_predictions()
        matches = self.football_data_world_cup_matches()
        group_by_pair = {
            (normalize_name(match["home_team"]), normalize_name(match["away_team"])): match["group"].replace("GROUP_", "Grupo ")
            for match in matches
            if match.get("group")
        }

        table: dict[str, dict[str, dict[str, float | str]]] = defaultdict(dict)
        for row in predictions:
            group = group_by_pair.get((row["home_team"], row["away_team"]), "Grupo pendiente")
            home = row["home_team"]
            away = row["away_team"]
            home_win = float(row["home_win_probability"]) / 100
            draw = float(row["draw_probability"]) / 100
            away_win = float(row["away_win_probability"]) / 100
            home_xg = float(row["home_expected_goals"])
            away_xg = float(row["away_expected_goals"])

            for team in (home, away):
                table[group].setdefault(
                    team,
                    {
                        "team": team,
                        "expected_points": 0.0,
                        "expected_goals_for": 0.0,
                        "expected_goals_against": 0.0,
                    },
                )

            table[group][home]["expected_points"] = float(table[group][home]["expected_points"]) + 3 * home_win + draw
            table[group][away]["expected_points"] = float(table[group][away]["expected_points"]) + 3 * away_win + draw
            table[group][home]["expected_goals_for"] = float(table[group][home]["expected_goals_for"]) + home_xg
            table[group][home]["expected_goals_against"] = float(table[group][home]["expected_goals_against"]) + away_xg
            table[group][away]["expected_goals_for"] = float(table[group][away]["expected_goals_for"]) + away_xg
            table[group][away]["expected_goals_against"] = float(table[group][away]["expected_goals_against"]) + home_xg

        groups = []
        third_places = []
        qualifiers = []
        for group, teams in sorted(table.items()):
            standings = sorted(
                teams.values(),
                key=lambda item: (
                    float(item["expected_points"]),
                    float(item["expected_goals_for"]) - float(item["expected_goals_against"]),
                    float(item["expected_goals_for"]),
                ),
                reverse=True,
            )
            formatted = []
            for index, item in enumerate(standings, start=1):
                row = {
                    "position": index,
                    "team": str(item["team"]),
                    "expected_points": round(float(item["expected_points"]), 2),
                    "expected_goal_difference": round(
                        float(item["expected_goals_for"]) - float(item["expected_goals_against"]), 2
                    ),
                    "expected_goals_for": round(float(item["expected_goals_for"]), 2),
                    "expected_goals_against": round(float(item["expected_goals_against"]), 2),
                }
                formatted.append(row)
                if index <= 2:
                    qualifiers.append(row)
                elif index == 3:
                    third_places.append(row)
            groups.append({"group": group, "standings": formatted})

        best_thirds = sorted(
            third_places,
            key=lambda item: (
                float(item["expected_points"]),
                float(item["expected_goal_difference"]),
                float(item["expected_goals_for"]),
            ),
            reverse=True,
        )[:8]
        qualifiers.extend(best_thirds)

        seeded = sorted(
            qualifiers,
            key=lambda item: (
                float(item["expected_points"]),
                float(item["expected_goal_difference"]),
                float(item["expected_goals_for"]),
            ),
            reverse=True,
        )

        rounds = []
        current = [item["team"] for item in seeded[:32]]
        round_names = ["Last 32", "Last 16", "Quarter-finals", "Semi-finals", "Final"]
        for round_name in round_names:
            pairings = []
            winners = []
            for i in range(len(current) // 2):
                team_a = current[i]
                team_b = current[-(i + 1)]
                prediction = self.predict_match(
                    str(team_a),
                    str(team_b),
                    match_date="2026-07-01",
                    neutral=1,
                    team_a_is_home=0,
                )
                probs = prediction["probabilities"]
                winner = str(team_a) if probs["team_a_win"] >= probs["team_b_win"] else str(team_b)
                if probs["draw"] > max(probs["team_a_win"], probs["team_b_win"]):
                    winner = str(team_a) if prediction["expected_goals"]["team_a"] >= prediction["expected_goals"]["team_b"] else str(team_b)
                winners.append(winner)
                pairings.append(
                    {
                        "team_a": team_a,
                        "team_b": team_b,
                        "winner": winner,
                        "team_a_win": probs["team_a_win"],
                        "draw": probs["draw"],
                        "team_b_win": probs["team_b_win"],
                        "top_score": prediction["top_scorelines"][0]["score"],
                    }
                )
            rounds.append({"round": round_name, "matches": pairings})
            current = winners
            if len(current) == 1:
                break

        return {
            "groups": groups,
            "best_thirds": best_thirds,
            "qualifiers": seeded[:32],
            "bracket": rounds,
            "projected_champion": current[0] if current else "",
        }

    def _history_before(self, team: str, match_date: date) -> list[dict[str, Any]]:
        return [match for match in self.team_history.get(team, []) if match["date"] < match_date]

    def build_features(
        self,
        team_a: str,
        team_b: str,
        match_date: str | date | None = None,
        is_home: int = 0,
        neutral: int = 1,
    ) -> dict[str, float]:
        team_a = normalize_name(team_a)
        team_b = normalize_name(team_b)
        date_value = parse_date(match_date)

        elo_team = value_before(self.elo_series, team_a, date_value, "elo", strict=True)
        elo_opponent = value_before(self.elo_series, team_b, date_value, "elo", strict=True)
        rank_team = value_before(self.fifa_series, team_a, date_value, "rank", strict=False)
        rank_opponent = value_before(self.fifa_series, team_b, date_value, "rank", strict=False)
        points_team = value_before(self.fifa_series, team_a, date_value, "total_points", strict=False)
        points_opponent = value_before(self.fifa_series, team_b, date_value, "total_points", strict=False)

        history_a = self._history_before(team_a, date_value)
        history_b = self._history_before(team_b, date_value)
        stats_5 = recent_stats(history_a, 5)
        stats_10 = recent_stats(history_a, 10)
        opponent_stats_5 = recent_stats(history_b, 5)
        opponent_stats_10 = recent_stats(history_b, 10)

        features: dict[str, float] = {
            "is_home": float(is_home),
            "neutral": float(neutral),
            "elo_team": elo_team,
            "elo_opponent": elo_opponent,
            "elo_diff": diff(elo_team, elo_opponent),
            "fifa_rank_team": rank_team,
            "fifa_rank_opponent": rank_opponent,
            "fifa_rank_diff": diff(rank_team, rank_opponent),
            "fifa_points_team": points_team,
            "fifa_points_opponent": points_opponent,
            "fifa_points_diff": diff(points_team, points_opponent),
        }
        features.update({key: float(value) for key, value in stats_5.items()})
        features.update({key: float(value) for key, value in stats_10.items()})

        opponent_prefixes = {
            **{f"opponent_{key}": value for key, value in opponent_stats_5.items()},
            **{f"opponent_{key}": value for key, value in opponent_stats_10.items()},
        }
        features.update({key: float(value) for key, value in opponent_prefixes.items()})

        for window in (5, 10):
            for key in (stats_5 if window == 5 else stats_10):
                metric = key.removesuffix(f"_last_{window}")
                own_key = f"{metric}_last_{window}"
                opponent_key = f"opponent_{metric}_last_{window}"
                features[f"{metric}_last_{window}_diff"] = (
                    features[own_key] - features[opponent_key]
                )
        return features

    def _feature_array(self, features: dict[str, float]) -> np.ndarray:
        return np.array([[features[column] for column in self.feature_columns]], dtype=float)

    def predict_match(
        self,
        team_a: str,
        team_b: str,
        match_date: str | date | None = None,
        neutral: int = 1,
        team_a_is_home: int = 0,
        max_goals: int = 6,
    ) -> dict[str, Any]:
        team_a = normalize_name(team_a)
        team_b = normalize_name(team_b)
        date_value = parse_date(match_date)

        features_a = self.build_features(
            team_a,
            team_b,
            date_value,
            is_home=team_a_is_home,
            neutral=neutral,
        )
        features_b = self.build_features(
            team_b,
            team_a,
            date_value,
            is_home=0 if team_a_is_home else (0 if neutral else 1),
            neutral=neutral,
        )

        class_probabilities = self.classification_model.predict_proba(
            self._feature_array(features_a)
        )[0]
        class_order = list(self.classification_model.classes_)
        probability_by_label = {
            TARGET_LABELS[int(label)]: float(class_probabilities[index])
            for index, label in enumerate(class_order)
        }

        expected_goals_a = float(self.score_model.predict(self._feature_array(features_a))[0])
        expected_goals_b = float(self.score_model.predict(self._feature_array(features_b))[0])
        expected_goals_a = max(expected_goals_a, 0.01)
        expected_goals_b = max(expected_goals_b, 0.01)

        scorelines = []
        for goals_a in range(max_goals + 1):
            prob_a = poisson_probability(expected_goals_a, goals_a)
            for goals_b in range(max_goals + 1):
                probability = prob_a * poisson_probability(expected_goals_b, goals_b)
                scorelines.append(
                    {
                        "score": f"{goals_a}-{goals_b}",
                        "team_a_goals": goals_a,
                        "team_b_goals": goals_b,
                        "probability": probability,
                    }
                )
        scorelines.sort(key=lambda row: row["probability"], reverse=True)

        winner = team_a
        if probability_by_label["loss"] > probability_by_label["win"]:
            winner = team_b
        if probability_by_label["draw"] > max(
            probability_by_label["win"],
            probability_by_label["loss"],
        ):
            winner = "Draw"

        return {
            "team_a": team_a,
            "team_b": team_b,
            "match_date": date_value.isoformat(),
            "winner": winner,
            "probabilities": {
                "team_a_win": round(probability_by_label["win"] * 100, 2),
                "draw": round(probability_by_label["draw"] * 100, 2),
                "team_b_win": round(probability_by_label["loss"] * 100, 2),
            },
            "expected_goals": {
                "team_a": round(expected_goals_a, 3),
                "team_b": round(expected_goals_b, 3),
            },
            "top_scorelines": [
                {
                    "score": row["score"],
                    "probability": round(row["probability"] * 100, 2),
                }
                for row in scorelines[:10]
            ],
        }
