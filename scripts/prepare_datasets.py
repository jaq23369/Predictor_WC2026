from __future__ import annotations

import csv
import re
from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

RESULTS_PATH = (
    RAW_DIR
    / "International football results from 1872 to 2026"
    / "results.csv"
)
FORMER_NAMES_PATH = (
    RAW_DIR
    / "International football results from 1872 to 2026"
    / "former_names.csv"
)
ELO_PATH = (
    RAW_DIR
    / "International Football Elo Ratings (1872-2025)"
    / "eloratings.csv"
)
FIFA_PATH = RAW_DIR / "FIFA Men's World Ranking" / "fifa_mens_rank.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_date(value: str) -> date:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value}")


def parse_optional_int(value: str) -> int | None:
    if value in ("", "NA", None):
        return None
    return int(float(value))


def parse_optional_float(value: str) -> float | None:
    if value in ("", "NA", None):
        return None
    return float(value)


def clean_name(value: str) -> str:
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def build_country_name_map() -> dict[str, str]:
    country_map: dict[str, str] = {}
    for row in read_csv(FORMER_NAMES_PATH):
        current = clean_name(row["current"])
        former = clean_name(row["former"])
        country_map[former] = current
        country_map[current] = current

    country_map.update(
        {
            "USA": "United States",
            "US Virgin Islands": "United States Virgin Islands",
            "U.S. Virgin Islands": "United States Virgin Islands",
            "Korea Republic": "South Korea",
            "IR Iran": "Iran",
            "Ivory Coast": "Côte d'Ivoire",
            "Cote d'Ivoire": "Côte d'Ivoire",
            "Czech Republic": "Czechia",
            "Cape Verde Islands": "Cape Verde",
            "Türkiye": "Turkey",
            "Chinese Taipei": "Taiwan",
            "Eastern Samoa": "American Samoa",
            "Democratic Republic of Congo": "DR Congo",
            "Congo DR": "DR Congo",
            "Zaire": "DR Congo",
            "Zaïre": "DR Congo",
        }
    )
    return country_map


COUNTRY_MAP = build_country_name_map()


def normalize_team(value: str) -> str:
    name = clean_name(value)
    return COUNTRY_MAP.get(name, name)


def bool_to_int(value: str) -> int:
    return 1 if str(value).strip().upper() == "TRUE" else 0


def result_for_team(goals_for: int, goals_against: int) -> tuple[int, str]:
    if goals_for > goals_against:
        return 2, "win"
    if goals_for == goals_against:
        return 1, "draw"
    return 0, "loss"


def clean_results() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    clean_matches: list[dict[str, object]] = []
    fixtures: list[dict[str, object]] = []

    for row in read_csv(RESULTS_PATH):
        match_date = parse_date(row["date"]).isoformat()
        home_score = parse_optional_int(row["home_score"])
        away_score = parse_optional_int(row["away_score"])
        clean_row = {
            "date": match_date,
            "home_team": normalize_team(row["home_team"]),
            "away_team": normalize_team(row["away_team"]),
            "home_score": "" if home_score is None else home_score,
            "away_score": "" if away_score is None else away_score,
            "tournament": clean_name(row["tournament"]),
            "city": clean_name(row["city"]),
            "country": normalize_team(row["country"]),
            "neutral": bool_to_int(row["neutral"]),
        }

        if home_score is None or away_score is None:
            fixtures.append(clean_row)
        else:
            home_target, home_result = result_for_team(home_score, away_score)
            clean_row["home_result"] = home_result
            clean_row["away_result"] = result_for_team(away_score, home_score)[1]
            clean_row["result_target_home"] = home_target
            clean_matches.append(clean_row)

    clean_matches.sort(key=lambda row: row["date"])
    fixtures.sort(key=lambda row: row["date"])
    return clean_matches, fixtures


def clean_elo() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in read_csv(ELO_PATH):
        rating = parse_optional_int(row["rating"])
        if rating is None:
            continue
        rows.append(
            {
                "date": parse_date(row["date"]).isoformat(),
                "team": normalize_team(row["team"]),
                "elo": rating,
                "elo_change": parse_optional_int(row["change"]),
            }
        )

    rows.sort(key=lambda row: (row["date"], row["team"]))
    return rows


def ranking_semester_date(year: int, semester: int) -> date:
    if semester == 1:
        return date(year, 6, 30)
    return date(year, 12, 31)


def clean_fifa_rankings() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in read_csv(FIFA_PATH):
        year = int(row["date"])
        semester = int(row["semester"])
        rows.append(
            {
                "ranking_date": ranking_semester_date(year, semester).isoformat(),
                "year": year,
                "semester": semester,
                "rank": int(row["rank"]),
                "team": normalize_team(row["team"]),
                "acronym": clean_name(row["acronym"]),
                "total_points": parse_optional_float(row["total.points"]),
                "previous_points": parse_optional_float(row["previous.points"]),
                "diff_points": parse_optional_float(row["diff.points"]),
            }
        )

    rows.sort(key=lambda row: (row["ranking_date"], row["rank"], row["team"]))
    return rows


def build_time_series(
    rows: list[dict[str, object]],
    team_key: str,
    date_key: str,
    value_keys: list[str],
) -> dict[str, dict[str, list[object]]]:
    series: dict[str, dict[str, list[object]]] = defaultdict(lambda: {"dates": []})
    for row in rows:
        team = str(row[team_key])
        row_date = parse_date(str(row[date_key]))
        series[team]["dates"].append(row_date)
        for value_key in value_keys:
            series[team].setdefault(value_key, []).append(row[value_key])
    return series


def value_before(
    series: dict[str, dict[str, list[object]]],
    team: str,
    match_date: date,
    value_key: str,
    strict: bool = True,
) -> object:
    team_series = series.get(team)
    if not team_series:
        return ""

    dates = team_series["dates"]
    index = bisect_left(dates, match_date) - 1 if strict else bisect_right(dates, match_date) - 1
    if index < 0:
        return ""
    return team_series[value_key][index]


def recent_stats(history: list[dict[str, object]], n: int) -> dict[str, object]:
    recent = history[-n:]
    if not recent:
        return {
            f"wins_last_{n}": "",
            f"draws_last_{n}": "",
            f"losses_last_{n}": "",
            f"points_last_{n}": "",
            f"goals_scored_last_{n}": "",
            f"goals_conceded_last_{n}": "",
            f"avg_goals_scored_last_{n}": "",
            f"avg_goals_conceded_last_{n}": "",
            f"clean_sheets_last_{n}": "",
            f"weighted_form_last_{n}": "",
            f"avg_opponent_elo_last_{n}": "",
            f"wins_vs_top30_last_{n}": "",
            f"points_vs_top30_last_{n}": "",
            f"wins_vs_top50_last_{n}": "",
            f"points_vs_top50_last_{n}": "",
            f"elo_change_last_{n}": "",
        }

    wins = sum(1 for match in recent if match["result"] == "win")
    draws = sum(1 for match in recent if match["result"] == "draw")
    losses = sum(1 for match in recent if match["result"] == "loss")
    points_by_result = {"win": 3, "draw": 1, "loss": 0}
    points = sum(points_by_result[str(match["result"])] for match in recent)
    goals_for = sum(int(match["goals_for"]) for match in recent)
    goals_against = sum(int(match["goals_against"]) for match in recent)
    clean_sheets = sum(1 for match in recent if int(match["goals_against"]) == 0)
    weights = list(range(1, len(recent) + 1))
    weighted_points = sum(
        points_by_result[str(match["result"])] * weight
        for match, weight in zip(recent, weights)
    )
    weight_total = sum(weights)
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
        f"avg_goals_scored_last_{n}": round(goals_for / count, 4),
        f"avg_goals_conceded_last_{n}": round(goals_against / count, 4),
        f"clean_sheets_last_{n}": clean_sheets,
        f"weighted_form_last_{n}": round(weighted_points / weight_total, 4),
        f"avg_opponent_elo_last_{n}": round(sum(opponent_elos) / len(opponent_elos), 4)
        if opponent_elos
        else "",
        f"wins_vs_top30_last_{n}": sum(
            1 for match in top30_matches if match["result"] == "win"
        ),
        f"points_vs_top30_last_{n}": sum(
            points_by_result[str(match["result"])] for match in top30_matches
        ),
        f"wins_vs_top50_last_{n}": sum(
            1 for match in top50_matches if match["result"] == "win"
        ),
        f"points_vs_top50_last_{n}": sum(
            points_by_result[str(match["result"])] for match in top50_matches
        ),
        f"elo_change_last_{n}": round(elo_values[-1] - elo_values[0], 4)
        if len(elo_values) >= 2
        else "",
    }


def diff(value_a: object, value_b: object, inverse: bool = False) -> object:
    if value_a == "" or value_b == "":
        return ""
    result = float(value_a) - float(value_b)
    if inverse:
        result *= -1
    if result.is_integer():
        return int(result)
    return round(result, 4)


def build_training_dataset(
    matches: list[dict[str, object]],
    elo_rows: list[dict[str, object]],
    fifa_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    elo_series = build_time_series(elo_rows, "team", "date", ["elo"])
    fifa_series = build_time_series(fifa_rows, "team", "ranking_date", ["rank", "total_points"])
    history: dict[str, list[dict[str, object]]] = defaultdict(list)
    training_rows: list[dict[str, object]] = []

    for match in matches:
        match_date = parse_date(str(match["date"]))
        home_team = str(match["home_team"])
        away_team = str(match["away_team"])
        home_score = int(match["home_score"])
        away_score = int(match["away_score"])

        for team_a, team_b, goals_for, goals_against, is_home in (
            (home_team, away_team, home_score, away_score, 1),
            (away_team, home_team, away_score, home_score, 0),
        ):
            target, result_label = result_for_team(goals_for, goals_against)
            elo_team = value_before(elo_series, team_a, match_date, "elo", strict=True)
            elo_opponent = value_before(elo_series, team_b, match_date, "elo", strict=True)
            rank_team = value_before(fifa_series, team_a, match_date, "rank", strict=False)
            rank_opponent = value_before(fifa_series, team_b, match_date, "rank", strict=False)
            points_team = value_before(fifa_series, team_a, match_date, "total_points", strict=False)
            points_opponent = value_before(fifa_series, team_b, match_date, "total_points", strict=False)

            stats_5 = recent_stats(history[team_a], 5)
            stats_10 = recent_stats(history[team_a], 10)
            opponent_stats_5 = recent_stats(history[team_b], 5)
            opponent_stats_10 = recent_stats(history[team_b], 10)

            row = {
                "match_date": match["date"],
                "tournament": match["tournament"],
                "team_a": team_a,
                "team_b": team_b,
                "is_home": is_home,
                "neutral": match["neutral"],
                "goals_for": goals_for,
                "goals_against": goals_against,
                "result": result_label,
                "target": target,
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
            row.update(stats_5)
            row.update(stats_10)
            row.update({f"opponent_{key}": value for key, value in opponent_stats_5.items()})
            row.update({f"opponent_{key}": value for key, value in opponent_stats_10.items()})

            for n in (5, 10):
                for metric in (
                    "wins",
                    "draws",
                    "losses",
                    "points",
                    "goals_scored",
                    "goals_conceded",
                    "avg_goals_scored",
                    "avg_goals_conceded",
                    "clean_sheets",
                    "weighted_form",
                    "avg_opponent_elo",
                    "wins_vs_top30",
                    "points_vs_top30",
                    "wins_vs_top50",
                    "points_vs_top50",
                    "elo_change",
                ):
                    row[f"{metric}_last_{n}_diff"] = diff(
                        row[f"{metric}_last_{n}"],
                        row[f"opponent_{metric}_last_{n}"],
                    )
            training_rows.append(row)

        home_result = result_for_team(home_score, away_score)[1]
        away_result = result_for_team(away_score, home_score)[1]
        home_elo = value_before(elo_series, home_team, match_date, "elo", strict=True)
        away_elo = value_before(elo_series, away_team, match_date, "elo", strict=True)
        home_rank = value_before(fifa_series, home_team, match_date, "rank", strict=False)
        away_rank = value_before(fifa_series, away_team, match_date, "rank", strict=False)
        history[home_team].append(
            {
                "goals_for": home_score,
                "goals_against": away_score,
                "result": home_result,
                "team_elo": home_elo,
                "opponent_elo": away_elo,
                "opponent_rank": away_rank,
            }
        )
        history[away_team].append(
            {
                "goals_for": away_score,
                "goals_against": home_score,
                "result": away_result,
                "team_elo": away_elo,
                "opponent_elo": home_elo,
                "opponent_rank": home_rank,
            }
        )

    return training_rows


def filter_rows_from_date(
    rows: list[dict[str, object]], date_key: str, start_date: str
) -> list[dict[str, object]]:
    return [row for row in rows if str(row[date_key]) >= start_date]


def filter_complete_rows(
    rows: list[dict[str, object]], required_fields: list[str]
) -> list[dict[str, object]]:
    return [
        row
        for row in rows
        if all(row.get(field) not in ("", None) for field in required_fields)
    ]


MATCHES_FIELDNAMES = [
    "date",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "tournament",
    "city",
    "country",
    "neutral",
    "home_result",
    "away_result",
    "result_target_home",
]

FIXTURES_FIELDNAMES = [
    "date",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "tournament",
    "city",
    "country",
    "neutral",
]

ELO_FIELDNAMES = ["date", "team", "elo", "elo_change"]

FIFA_FIELDNAMES = [
    "ranking_date",
    "year",
    "semester",
    "rank",
    "team",
    "acronym",
    "total_points",
    "previous_points",
    "diff_points",
]

BASE_FEATURE_FIELDNAMES = [
    "match_date",
    "tournament",
    "team_a",
    "team_b",
    "is_home",
    "neutral",
    "goals_for",
    "goals_against",
    "elo_team",
    "elo_opponent",
    "elo_diff",
    "fifa_rank_team",
    "fifa_rank_opponent",
    "fifa_rank_diff",
    "fifa_points_team",
    "fifa_points_opponent",
    "fifa_points_diff",
]

FORM_METRICS = [
    "wins",
    "draws",
    "losses",
    "points",
    "goals_scored",
    "goals_conceded",
    "avg_goals_scored",
    "avg_goals_conceded",
    "clean_sheets",
    "weighted_form",
    "avg_opponent_elo",
    "wins_vs_top30",
    "points_vs_top30",
    "wins_vs_top50",
    "points_vs_top50",
    "elo_change",
]

FORM_FIELDNAMES = [
    f"{metric}_last_{window}"
    for window in (5, 10)
    for metric in FORM_METRICS
]

OPPONENT_FORM_FIELDNAMES = [
    f"opponent_{field}" for field in FORM_FIELDNAMES
]

FORM_DIFF_FIELDNAMES = [
    f"{metric}_last_{window}_diff"
    for window in (5, 10)
    for metric in FORM_METRICS
]

TRAINING_FIELDNAMES = [
    *BASE_FEATURE_FIELDNAMES,
    *FORM_FIELDNAMES,
    *OPPONENT_FORM_FIELDNAMES,
    *FORM_DIFF_FIELDNAMES,
    "result",
    "target",
]

FINAL_TRAINING_FIELDNAMES = [
    field
    for field in TRAINING_FIELDNAMES
    if field not in ("goals_for", "goals_against")
]


def main() -> None:
    matches, fixtures = clean_results()
    elo_rows = clean_elo()
    fifa_rows = clean_fifa_rankings()
    training_rows = build_training_dataset(matches, elo_rows, fifa_rows)
    modern_training_rows = filter_rows_from_date(
        training_rows, "match_date", "1993-01-01"
    )
    model_ready_rows = filter_complete_rows(
        modern_training_rows,
        [
            field
            for field in FINAL_TRAINING_FIELDNAMES
            if field
            not in ("match_date", "tournament", "team_a", "team_b", "result", "target")
        ],
    )
    final_training_rows = [
        {field: row[field] for field in FINAL_TRAINING_FIELDNAMES}
        for row in model_ready_rows
    ]

    write_csv(PROCESSED_DIR / "matches_clean.csv", matches, MATCHES_FIELDNAMES)
    write_csv(PROCESSED_DIR / "world_cup_2026_fixtures.csv", fixtures, FIXTURES_FIELDNAMES)
    write_csv(PROCESSED_DIR / "elo_clean.csv", elo_rows, ELO_FIELDNAMES)
    write_csv(PROCESSED_DIR / "fifa_rankings_clean.csv", fifa_rows, FIFA_FIELDNAMES)
    write_csv(PROCESSED_DIR / "training_matches.csv", training_rows, TRAINING_FIELDNAMES)
    write_csv(
        PROCESSED_DIR / "training_matches_modern.csv",
        modern_training_rows,
        TRAINING_FIELDNAMES,
    )
    write_csv(
        PROCESSED_DIR / "training_matches_model_ready.csv",
        model_ready_rows,
        TRAINING_FIELDNAMES,
    )
    write_csv(
        PROCESSED_DIR / "final_training_dataset.csv",
        final_training_rows,
        FINAL_TRAINING_FIELDNAMES,
    )

    print(f"matches_clean.csv: {len(matches):,} rows")
    print(f"world_cup_2026_fixtures.csv: {len(fixtures):,} rows")
    print(f"elo_clean.csv: {len(elo_rows):,} rows")
    print(f"fifa_rankings_clean.csv: {len(fifa_rows):,} rows")
    print(f"training_matches.csv: {len(training_rows):,} rows")
    print(f"training_matches_modern.csv: {len(modern_training_rows):,} rows")
    print(f"training_matches_model_ready.csv: {len(model_ready_rows):,} rows")
    print(f"final_training_dataset.csv: {len(final_training_rows):,} rows")


if __name__ == "__main__":
    main()
