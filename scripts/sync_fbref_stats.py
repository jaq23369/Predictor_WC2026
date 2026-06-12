from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
SOCCERDATA_CACHE_DIR = ROOT_DIR / "data" / "api_cache" / "soccerdata" / "FBref"

DEFAULT_LEAGUE = "INT-World Cup"
DEFAULT_SEASONS = ["2022", "2026"]

TEAM_ALIASES = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Cape Verde Islands": "Cape Verde",
    "Cabo Verde": "Cape Verde",
    "Congo DR": "DR Congo",
    "Cote d'Ivoire": "Côte d'Ivoire",
    "Ivory Coast": "Côte d'Ivoire",
    "IR Iran": "Iran",
    "Korea Republic": "South Korea",
    "Türkiye": "Turkey",
    "Turkiye": "Turkey",
    "United States of America": "United States",
    "USA": "United States",
}

NUMERIC_FEATURES = {
    "xg": "avg_xg_for",
    "xga": "avg_xg_against",
    "sh": "avg_shots",
    "sot": "avg_shots_on_target",
    "dist": "avg_shot_distance",
    "fk": "avg_free_kick_shots",
    "pk": "avg_penalty_goals",
    "pkatt": "avg_penalty_attempts",
    "crdy": "avg_yellow_cards",
    "crdr": "avg_red_cards",
    "fls": "avg_fouls",
    "fld": "avg_fouls_drawn",
    "off": "avg_offsides",
    "crs": "avg_crosses",
    "tklw": "avg_tackles_won",
    "int": "avg_interceptions",
    "og": "avg_own_goals",
}


def normalize_team(value: Any) -> str:
    name = " ".join(str(value or "").replace("\xa0", " ").split()).strip()
    return TEAM_ALIASES.get(name, name)


def normalize_column(value: Any) -> str:
    if isinstance(value, tuple):
        parts = [str(part) for part in value if str(part) and not str(part).startswith("Unnamed")]
        value = "_".join(parts)
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return "_".join(text.lower().replace("%", "pct").replace("+/-", "diff").split()).strip("_")


def flatten_dataframe(dataframe: Any) -> Any:
    dataframe = dataframe.copy()
    dataframe.columns = [normalize_column(column) for column in dataframe.columns]
    dataframe = dataframe.reset_index()
    dataframe.columns = [normalize_column(column) for column in dataframe.columns]
    return dataframe


def first_existing(row: dict[str, Any], candidates: list[str]) -> Any:
    for candidate in candidates:
        if candidate in row and row[candidate] not in ("", None):
            return row[candidate]
    return ""


def numeric(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(str(value).replace("%", "").strip())
    except ValueError:
        return None


def score_number(value: str) -> str:
    matches = re.findall(r"\d+", str(value or ""))
    return matches[-1] if matches else ""


def result_code(goals_for: str, goals_against: str) -> str:
    if not goals_for or not goals_against:
        return ""
    left = int(goals_for)
    right = int(goals_against)
    if left > right:
        return "W"
    if left == right:
        return "D"
    return "L"


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def dataframe_to_rows(dataframe: Any, source: str) -> list[dict[str, Any]]:
    rows = []
    for raw in flatten_dataframe(dataframe).to_dict("records"):
        if source == "schedule" and raw.get("home_team") and raw.get("away_team"):
            score = str(raw.get("score") or "")
            home_score = away_score = ""
            if "–" in score:
                left, right = score.split("–", 1)
                home_score = score_number(left)
                away_score = score_number(right)
            elif "-" in score:
                left, right = score.split("-", 1)
                home_score = score_number(left)
                away_score = score_number(right)

            home_team = normalize_team(raw.get("home_team"))
            away_team = normalize_team(raw.get("away_team"))
            base = {
                "source": source,
                "season": first_existing(raw, ["season"]),
                "date": first_existing(raw, ["date", "match_date"]),
                "venue": first_existing(raw, ["venue"]),
                "result": "",
                "xg": first_existing(raw, ["home_xg", "xg_home", "home_team_xg"]),
                "xga": first_existing(raw, ["away_xg", "xg_away", "away_team_xg"]),
            }
            rows.append(
                {
                    **base,
                    "team": home_team,
                    "opponent": away_team,
                    "goals_for": home_score,
                    "goals_against": away_score,
                    "result": result_code(home_score, away_score),
                }
            )
            rows.append(
                {
                    **base,
                    "team": away_team,
                    "opponent": home_team,
                    "goals_for": away_score,
                    "goals_against": home_score,
                    "xg": first_existing(raw, ["away_xg", "xg_away", "away_team_xg"]),
                    "xga": first_existing(raw, ["home_xg", "xg_home", "home_team_xg"]),
                    "result": result_code(away_score, home_score),
                }
            )
            continue

        team = normalize_team(first_existing(raw, ["team", "squad", "team_name"]))
        opponent = normalize_team(first_existing(raw, ["opponent", "opp", "opponent_name"]))
        date = first_existing(raw, ["date", "match_date"])
        rows.append(
            {
                "source": source,
                "season": first_existing(raw, ["season"]),
                "date": date,
                "team": team,
                "opponent": opponent,
                "venue": first_existing(raw, ["venue"]),
                "result": first_existing(raw, ["result"]),
                "goals_for": first_existing(raw, ["gf", "goals_for"]),
                "goals_against": first_existing(raw, ["ga", "goals_against"]),
                "xg": first_existing(raw, ["xg", "performance_xg", "expected_xg"]),
                "xga": first_existing(raw, ["xga", "expected_xga"]),
                "sh": first_existing(raw, ["sh", "standard_sh", "shooting_sh"]),
                "sot": first_existing(raw, ["sot", "standard_sot", "shooting_sot"]),
                "dist": first_existing(raw, ["dist", "standard_dist", "shooting_dist"]),
                "fk": first_existing(raw, ["fk", "standard_fk", "shooting_fk"]),
                "pk": first_existing(raw, ["pk", "standard_pk"]),
                "pkatt": first_existing(raw, ["pkatt", "standard_pkatt"]),
                "crdy": first_existing(raw, ["crdy", "performance_crdy", "misc_crdy"]),
                "crdr": first_existing(raw, ["crdr", "performance_crdr", "misc_crdr"]),
                "fls": first_existing(raw, ["fls", "performance_fls", "misc_fls"]),
                "fld": first_existing(raw, ["fld", "performance_fld", "misc_fld"]),
                "off": first_existing(raw, ["off", "performance_off", "misc_off"]),
                "crs": first_existing(raw, ["crs", "performance_crs", "misc_crs"]),
                "tklw": first_existing(raw, ["tklw", "performance_tklw", "misc_tklw"]),
                "int": first_existing(raw, ["int", "performance_int", "misc_int"]),
                "og": first_existing(raw, ["og", "performance_og", "misc_og"]),
            }
        )
    return rows


def merge_rows(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in [*existing, *incoming]:
        key = (str(row.get("date", "")), str(row.get("team", "")), str(row.get("opponent", "")), str(row.get("source", "")))
        current = merged.setdefault(key, {})
        for field, value in row.items():
            if value not in ("", None):
                current[field] = value
            elif field not in current:
                current[field] = value
    return sorted(
        merged.values(),
        key=lambda row: (str(row.get("date", "")), str(row.get("team", "")), str(row.get("opponent", "")), str(row.get("source", ""))),
    )


def summarize_team_features(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_team: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        team = normalize_team(row.get("team"))
        if not team:
            continue
        by_team.setdefault(team, []).append(row)

    summary_rows = []
    for team, team_rows in sorted(by_team.items()):
        finished_rows = [
            row for row in team_rows if row.get("date")
        ]
        summary: dict[str, Any] = {
            "team": team,
            "matches_with_fbref": len(finished_rows),
        }
        for source in ("shooting", "misc", "schedule"):
            summary[f"{source}_rows"] = sum(1 for row in finished_rows if row.get("source") == source)

        for raw_key, output_key in NUMERIC_FEATURES.items():
            values = [numeric(row.get(raw_key)) for row in finished_rows]
            values = [value for value in values if value is not None]
            summary[output_key] = round(sum(values) / len(values), 4) if values else ""

        xg = numeric(summary.get("avg_xg_for"))
        xga = numeric(summary.get("avg_xg_against"))
        summary["avg_xg_diff"] = round(xg - xga, 4) if xg is not None and xga is not None else ""
        summary_rows.append(summary)

    return summary_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync FBref advanced stats through soccerdata.")
    parser.add_argument("--league", default=DEFAULT_LEAGUE, help="soccerdata FBref league id.")
    parser.add_argument("--seasons", nargs="+", default=DEFAULT_SEASONS, help="Seasons to request.")
    parser.add_argument("--stat-types", nargs="+", default=["schedule"], choices=["schedule", "shooting", "misc"])
    parser.add_argument("--delay", type=float, default=4.0, help="Seconds to wait between stat-type requests.")
    parser.add_argument("--force-cache", action="store_true", help="Force soccerdata cache for current season.")
    args = parser.parse_args()

    try:
        import soccerdata as sd
    except ModuleNotFoundError as error:
        raise SystemExit(
            "Falta soccerdata. Instala dependencias offline con:\n"
            ".venv/bin/pip install -r requirements-offline.txt"
        ) from error

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    SOCCERDATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    fbref = sd.FBref(
        leagues=args.league,
        seasons=args.seasons,
        data_dir=SOCCERDATA_CACHE_DIR,
    )

    all_rows: list[dict[str, Any]] = []
    coverage_rows = [
        {"metric": "league", "value": args.league},
        {"metric": "seasons", "value": ",".join(str(season) for season in args.seasons)},
    ]

    for index, stat_type in enumerate(args.stat_types):
        try:
            if stat_type == "schedule":
                frame = fbref.read_schedule(force_cache=args.force_cache)
            else:
                frame = fbref.read_team_match_stats(stat_type=stat_type, force_cache=args.force_cache)
            rows = dataframe_to_rows(frame, stat_type)
            all_rows = merge_rows(all_rows, rows)
            coverage_rows.append({"metric": f"{stat_type}_rows", "value": len(rows)})
        except Exception as error:  # soccerdata can break when FBref changes layout.
            coverage_rows.append({"metric": f"{stat_type}_error", "value": str(error)})
        if index < len(args.stat_types) - 1 and args.delay > 0:
            time.sleep(args.delay)

    match_stats_path = PROCESSED_DIR / "fbref_team_match_stats.csv"
    feature_path = PROCESSED_DIR / "fbref_team_form_features.csv"
    coverage_path = PROCESSED_DIR / "fbref_coverage.csv"

    match_fields = [
        "source",
        "season",
        "date",
        "team",
        "opponent",
        "venue",
        "result",
        "goals_for",
        "goals_against",
        *NUMERIC_FEATURES.keys(),
    ]
    feature_fields = [
        "team",
        "matches_with_fbref",
        "schedule_rows",
        "shooting_rows",
        "misc_rows",
        *NUMERIC_FEATURES.values(),
        "avg_xg_diff",
    ]

    feature_rows = summarize_team_features(all_rows)
    coverage_rows.extend(
        [
            {"metric": "total_rows", "value": len(all_rows)},
            {"metric": "teams_with_fbref", "value": len(feature_rows)},
        ]
    )

    write_csv(match_stats_path, all_rows, match_fields)
    write_csv(feature_path, feature_rows, feature_fields)
    write_csv(coverage_path, coverage_rows, ["metric", "value"])

    print(f"saved={match_stats_path}")
    print(f"saved={feature_path}")
    print(f"saved={coverage_path}")


if __name__ == "__main__":
    main()
