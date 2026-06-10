from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.football_data_service import (  # noqa: E402
    FootballDataClient,
    FootballDataError,
)


PROCESSED_DIR = ROOT_DIR / "data" / "processed"
API_CACHE_DIR = ROOT_DIR / "data" / "api_cache" / "football_data"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def flatten_matches(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for match in payload.get("matches", []):
        home = match.get("homeTeam") or {}
        away = match.get("awayTeam") or {}
        score = match.get("score") or {}
        full_time = score.get("fullTime") or {}
        group = match.get("group") or ""
        rows.append(
            {
                "match_id": match.get("id", ""),
                "utc_date": match.get("utcDate", ""),
                "status": match.get("status", ""),
                "stage": match.get("stage", ""),
                "group": group,
                "matchday": match.get("matchday", ""),
                "home_team_id": home.get("id", ""),
                "home_team": home.get("name", ""),
                "home_team_tla": home.get("tla", ""),
                "away_team_id": away.get("id", ""),
                "away_team": away.get("name", ""),
                "away_team_tla": away.get("tla", ""),
                "winner": score.get("winner", ""),
                "home_score": full_time.get("home", ""),
                "away_score": full_time.get("away", ""),
                "last_updated": match.get("lastUpdated", ""),
            }
        )
    return rows


def flatten_teams(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for team in payload.get("teams", []):
        area = team.get("area") or {}
        rows.append(
            {
                "team_id": team.get("id", ""),
                "name": team.get("name", ""),
                "short_name": team.get("shortName", ""),
                "tla": team.get("tla", ""),
                "crest": team.get("crest", ""),
                "area_id": area.get("id", ""),
                "area_name": area.get("name", ""),
                "area_code": area.get("code", ""),
            }
        )
    return rows


def group_lookup_from_matches(matches: list[dict[str, Any]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for match in matches:
        group = match.get("group") or ""
        if not group:
            continue
        for key in ("home_team_id", "away_team_id"):
            team_id = str(match.get(key) or "")
            if team_id:
                lookup[team_id] = group
    return lookup


def flatten_standings(
    payload: dict[str, Any], team_id_to_group: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    team_id_to_group = team_id_to_group or {}
    rows = []
    for standing in payload.get("standings", []):
        group = standing.get("group") or ""
        stage = standing.get("stage", "")
        standing_type = standing.get("type", "")
        for item in standing.get("table", []):
            team = item.get("team") or {}
            team_id = str(team.get("id", ""))
            rows.append(
                {
                    "stage": stage,
                    "group": group or team_id_to_group.get(team_id, ""),
                    "type": standing_type,
                    "position": item.get("position", ""),
                    "team_id": team_id,
                    "team": team.get("name", ""),
                    "team_tla": team.get("tla", ""),
                    "played_games": item.get("playedGames", ""),
                    "won": item.get("won", ""),
                    "draw": item.get("draw", ""),
                    "lost": item.get("lost", ""),
                    "points": item.get("points", ""),
                    "goals_for": item.get("goalsFor", ""),
                    "goals_against": item.get("goalsAgainst", ""),
                    "goal_difference": item.get("goalDifference", ""),
                }
            )
    return rows


def flatten_scorers(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in payload.get("scorers", []):
        player = item.get("player") or {}
        team = item.get("team") or {}
        rows.append(
            {
                "player_id": player.get("id", ""),
                "player": player.get("name", ""),
                "team_id": team.get("id", ""),
                "team": team.get("name", ""),
                "goals": item.get("goals", ""),
                "assists": item.get("assists", ""),
                "penalties": item.get("penalties", ""),
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync football-data.org World Cup data.")
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument(
        "--from-cache",
        action="store_true",
        help="Regenerate processed CSVs from cached API JSON without calling football-data.org.",
    )
    parser.add_argument(
        "--include-scorers",
        action="store_true",
        help="Also fetch scorers. This may be empty before the tournament starts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.from_cache:
        try:
            matches_response = json.loads(
                (API_CACHE_DIR / f"wc_{args.season}_matches.json").read_text(encoding="utf-8")
            )
            teams_response = json.loads(
                (API_CACHE_DIR / f"wc_{args.season}_teams.json").read_text(encoding="utf-8")
            )
            standings_response = json.loads(
                (API_CACHE_DIR / f"wc_{args.season}_standings.json").read_text(encoding="utf-8")
            )
            scorers_path = API_CACHE_DIR / f"wc_{args.season}_scorers.json"
            scorers_response = (
                json.loads(scorers_path.read_text(encoding="utf-8"))
                if args.include_scorers and scorers_path.exists()
                else None
            )
        except FileNotFoundError as error:
            raise SystemExit(
                "No existe cache local suficiente. Ejecuta el sync sin --from-cache primero."
            ) from error
    else:
        client = FootballDataClient()

        try:
            matches_response = client.world_cup_matches(season=args.season)
            teams_response = client.world_cup_teams(season=args.season)
            standings_response = client.world_cup_standings(season=args.season)
            scorers_response = client.world_cup_scorers(season=args.season) if args.include_scorers else None
        except FootballDataError as error:
            raise SystemExit(str(error)) from error

        write_json(API_CACHE_DIR / f"wc_{args.season}_matches.json", matches_response)
        write_json(API_CACHE_DIR / f"wc_{args.season}_teams.json", teams_response)
        write_json(API_CACHE_DIR / f"wc_{args.season}_standings.json", standings_response)
        if scorers_response:
            write_json(API_CACHE_DIR / f"wc_{args.season}_scorers.json", scorers_response)

    matches = flatten_matches(matches_response["data"])
    teams = flatten_teams(teams_response["data"])
    standings = flatten_standings(
        standings_response["data"],
        team_id_to_group=group_lookup_from_matches(matches),
    )

    write_csv(
        PROCESSED_DIR / f"football_data_wc_{args.season}_matches.csv",
        matches,
        [
            "match_id",
            "utc_date",
            "status",
            "stage",
            "group",
            "matchday",
            "home_team_id",
            "home_team",
            "home_team_tla",
            "away_team_id",
            "away_team",
            "away_team_tla",
            "winner",
            "home_score",
            "away_score",
            "last_updated",
        ],
    )
    write_csv(
        PROCESSED_DIR / f"football_data_wc_{args.season}_teams.csv",
        teams,
        ["team_id", "name", "short_name", "tla", "crest", "area_id", "area_name", "area_code"],
    )
    write_csv(
        PROCESSED_DIR / f"football_data_wc_{args.season}_standings.csv",
        standings,
        [
            "stage",
            "group",
            "type",
            "position",
            "team_id",
            "team",
            "team_tla",
            "played_games",
            "won",
            "draw",
            "lost",
            "points",
            "goals_for",
            "goals_against",
            "goal_difference",
        ],
    )

    if scorers_response:
        scorers = flatten_scorers(scorers_response["data"])
        write_csv(
            PROCESSED_DIR / f"football_data_wc_{args.season}_scorers.csv",
            scorers,
            ["player_id", "player", "team_id", "team", "goals", "assists", "penalties"],
        )

    print(f"matches={len(matches)}")
    print(f"teams={len(teams)}")
    print(f"standings={len(standings)}")
    print(f"cache_dir={API_CACHE_DIR}")


if __name__ == "__main__":
    main()
