from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Callable


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.api_football_service import (  # noqa: E402
    APIFootballClient,
    APIFootballError,
)


PROCESSED_DIR = ROOT_DIR / "data" / "processed"
FIXTURES_PATH = PROCESSED_DIR / "world_cup_2026_fixtures.csv"
API_CACHE_DIR = ROOT_DIR / "data" / "api_cache" / "api_football"

TEAM_ALIASES = {
    "Bosnia and Herzegovina": ["Bosnia", "Bosnia-Herzegovina"],
    "Cape Verde": ["Cabo Verde"],
    "Côte d'Ivoire": ["Ivory Coast", "Cote d'Ivoire"],
    "Czechia": ["Czech Republic"],
    "DR Congo": ["Congo DR", "Democratic Republic of Congo"],
    "Iran": ["IR Iran"],
    "South Korea": ["Korea Republic"],
    "Turkey": ["Türkiye", "Turkiye"],
    "United States": ["USA", "United States of America"],
}

STAT_COLUMNS = {
    "shots_on_goal": "avg_shots_on_goal",
    "total_shots": "avg_total_shots",
    "fouls": "avg_fouls",
    "corner_kicks": "avg_corners",
    "yellow_cards": "avg_yellow_cards",
    "red_cards": "avg_red_cards",
    "ball_possession": "avg_possession",
}

FINISHED_STATUS = {"FT", "AET", "PEN"}


class RequestBudget:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.used = 0

    def can_fetch(self) -> bool:
        return self.used < self.limit

    def mark_fetch(self) -> None:
        self.used += 1


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower() or "unknown"


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(value.lower().replace("-", " ").replace(".", " ").split())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def cached_or_fetch(
    path: Path,
    fetch: Callable[[], dict[str, Any]],
    budget: RequestBudget,
    from_cache: bool,
) -> dict[str, Any]:
    if path.exists():
        return read_json(path)
    if from_cache or not budget.can_fetch():
        return {"data": {"response": []}, "headers": {}, "synced_at": "", "url": ""}
    budget.mark_fetch()
    payload = fetch()
    write_json(path, payload)
    return payload


def response_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") or {}
    items = data.get("response")
    return items if isinstance(items, list) else []


def world_cup_teams() -> list[str]:
    rows = read_csv(FIXTURES_PATH)
    teams = {row["home_team"] for row in rows} | {row["away_team"] for row in rows}
    return sorted(team for team in teams if team)


def search_names(team: str) -> list[str]:
    return [team, *TEAM_ALIASES.get(team, [])]


def choose_team(team: str, payloads: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    team_key = normalize_text(team)
    alias_keys = {normalize_text(name) for name in search_names(team)}
    candidates = []
    for payload in payloads:
        candidates.extend(response_items(payload))

    national = [item for item in candidates if (item.get("team") or {}).get("national") is True]
    pool = national or candidates
    if not pool:
        return None, "unmatched"

    for item in pool:
        candidate = item.get("team") or {}
        candidate_name = normalize_text(candidate.get("name", ""))
        candidate_country = normalize_text(item.get("country", ""))
        if candidate_name == team_key or candidate_name in alias_keys or candidate_country == team_key:
            return item, "exact"

    return pool[0], "fallback_national" if national else "fallback_first"


def flatten_mapping(team: str, chosen: dict[str, Any] | None, status: str) -> dict[str, Any]:
    team_data = (chosen or {}).get("team") or {}
    return {
        "team": team,
        "api_football_team_id": team_data.get("id", ""),
        "api_football_team": team_data.get("name", ""),
        "country": (chosen or {}).get("country", ""),
        "national": team_data.get("national", ""),
        "logo": team_data.get("logo", ""),
        "match_status": status,
    }


def flatten_fixtures(team: str, team_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in response_items(payload):
        fixture = item.get("fixture") or {}
        league = item.get("league") or {}
        teams = item.get("teams") or {}
        goals = item.get("goals") or {}
        home = teams.get("home") or {}
        away = teams.get("away") or {}
        is_home = str(home.get("id", "")) == str(team_id)
        goals_for = goals.get("home") if is_home else goals.get("away")
        goals_against = goals.get("away") if is_home else goals.get("home")
        rows.append(
            {
                "team": team,
                "api_football_team_id": team_id,
                "fixture_id": fixture.get("id", ""),
                "date": fixture.get("date", ""),
                "timestamp": fixture.get("timestamp", ""),
                "status": (fixture.get("status") or {}).get("short", ""),
                "league_id": league.get("id", ""),
                "league": league.get("name", ""),
                "season": league.get("season", ""),
                "round": league.get("round", ""),
                "home_team_id": home.get("id", ""),
                "home_team": home.get("name", ""),
                "away_team_id": away.get("id", ""),
                "away_team": away.get("name", ""),
                "opponent": away.get("name", "") if is_home else home.get("name", ""),
                "venue": "home" if is_home else "away",
                "goals_for": "" if goals_for is None else goals_for,
                "goals_against": "" if goals_against is None else goals_against,
            }
        )
    return rows


def stat_key(value: str) -> str:
    return slugify(value)


def numeric_stat(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(str(value).replace("%", "").strip())
    except ValueError:
        return None


def flatten_fixture_statistics(payload: dict[str, Any], fixture_lookup: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for team_stats in response_items(payload):
        team = team_stats.get("team") or {}
        fixture_id = str((payload.get("fixture_id") or ""))
        fixture = fixture_lookup.get(fixture_id, {})
        for stat in team_stats.get("statistics", []):
            rows.append(
                {
                    "fixture_id": fixture_id,
                    "date": fixture.get("date", ""),
                    "api_football_team_id": team.get("id", ""),
                    "team": team.get("name", ""),
                    "opponent": fixture.get("away_team", "") if str(team.get("id")) == str(fixture.get("home_team_id")) else fixture.get("home_team", ""),
                    "stat": stat_key(str(stat.get("type", ""))),
                    "raw_stat": stat.get("type", ""),
                    "value": "" if stat.get("value") is None else stat.get("value"),
                }
            )
    return rows


def summarize_team_stats(stats_rows: list[dict[str, Any]], team_mapping: dict[str, str]) -> list[dict[str, Any]]:
    by_team: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    events_by_team: dict[str, set[str]] = defaultdict(set)

    api_to_project_team = {value: key for key, value in team_mapping.items() if value}
    for row in stats_rows:
        project_team = api_to_project_team.get(str(row["api_football_team_id"]))
        if not project_team:
            continue
        if row["stat"] not in STAT_COLUMNS:
            continue
        value = numeric_stat(row["value"])
        if value is None:
            continue
        by_team[project_team][row["stat"]].append(value)
        events_by_team[project_team].add(str(row["fixture_id"]))

    rows = []
    for team, stats in sorted(by_team.items()):
        row: dict[str, Any] = {
            "team": team,
            "fixtures_with_stats": len(events_by_team[team]),
        }
        for stat, column in STAT_COLUMNS.items():
            values = stats.get(stat, [])
            row[column] = round(sum(values) / len(values), 3) if values else 0
        rows.append(row)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync API-Football stats for World Cup teams.")
    parser.add_argument("--daily-budget", type=int, default=95, help="Maximum uncached API requests for this run.")
    parser.add_argument("--season", type=int, default=2024)
    parser.add_argument("--from-date", default="2024-01-01", help="Start date for recent finished fixtures.")
    parser.add_argument("--to-date", default="2024-12-31", help="End date for recent finished fixtures.")
    parser.add_argument("--from-cache", action="store_true", help="Regenerate CSVs without calling API-Football.")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--request-delay", type=float, default=6.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    budget = RequestBudget(args.daily_budget)
    client = APIFootballClient(timeout=args.timeout, request_delay=args.request_delay)
    teams = world_cup_teams()

    mapping_rows = []
    fixture_rows = []
    fixture_lookup: dict[str, dict[str, Any]] = {}
    stats_rows = []
    seen_fixture_ids = []

    for index, team in enumerate(teams, start=1):
        print(f"[{index}/{len(teams)}] {team} budget={budget.used}/{budget.limit}", flush=True)
        team_slug = slugify(team)
        search_payloads = []
        for search_name in search_names(team):
            path = API_CACHE_DIR / "teams" / team_slug / f"search_{slugify(search_name)}.json"
            try:
                search_payloads.append(
                    cached_or_fetch(
                        path,
                        lambda search_name=search_name: client.search_team(search_name),
                        budget,
                        args.from_cache,
                    )
                )
            except APIFootballError as error:
                print(f"warning: search {team}: {error}")
            _, current_status = choose_team(team, search_payloads)
            if current_status == "exact":
                break

        chosen, status = choose_team(team, search_payloads)
        mapping = flatten_mapping(team, chosen, status)
        mapping_rows.append(mapping)
        team_id = str(mapping["api_football_team_id"])
        if not team_id:
            continue

        fixtures_path = API_CACHE_DIR / "fixtures" / f"{team_slug}_{args.from_date}_{args.to_date}.json"
        try:
            fixtures_payload = cached_or_fetch(
                fixtures_path,
                lambda team_id=team_id: client.team_fixtures_between(
                    team_id,
                    season=args.season,
                    from_date=args.from_date,
                    to_date=args.to_date,
                ),
                budget,
                args.from_cache,
            )
        except APIFootballError as error:
            print(f"warning: fixtures {team}: {error}")
            fixtures_payload = {"data": {"response": []}}
        rows = flatten_fixtures(team, team_id, fixtures_payload)
        fixture_rows.extend(rows)
        for row in rows:
            if row["fixture_id"]:
                fixture_lookup[str(row["fixture_id"])] = row
            fixture_id = str(row["fixture_id"])
            if not fixture_id or fixture_id in seen_fixture_ids or row["status"] not in FINISHED_STATUS:
                continue
            seen_fixture_ids.append(fixture_id)
            stats_path = API_CACHE_DIR / "fixture_statistics" / f"{fixture_id}.json"
            try:
                stats_payload = cached_or_fetch(
                    stats_path,
                    lambda fixture_id=fixture_id: client.fixture_statistics(fixture_id),
                    budget,
                    args.from_cache,
                )
                stats_payload["fixture_id"] = fixture_id
                stats_rows.extend(flatten_fixture_statistics(stats_payload, fixture_lookup))
            except APIFootballError as error:
                print(f"warning: stats fixture {fixture_id}: {error}")

    team_mapping = {
        row["team"]: str(row["api_football_team_id"])
        for row in mapping_rows
        if row["api_football_team_id"]
    }
    team_stats_rows = summarize_team_stats(stats_rows, team_mapping)
    coverage_rows = [
        {"metric": "request_budget", "value": budget.limit},
        {"metric": "requests_used", "value": budget.used},
        {"metric": "teams_total", "value": len(teams)},
        {"metric": "teams_matched", "value": sum(1 for row in mapping_rows if row["api_football_team_id"])},
        {"metric": "fixture_rows", "value": len(fixture_rows)},
        {"metric": "unique_fixtures", "value": len(seen_fixture_ids)},
        {"metric": "stat_rows", "value": len(stats_rows)},
        {"metric": "teams_with_stats", "value": len(team_stats_rows)},
    ]

    write_csv(
        PROCESSED_DIR / "api_football_team_mapping.csv",
        mapping_rows,
        ["team", "api_football_team_id", "api_football_team", "country", "national", "logo", "match_status"],
    )
    write_csv(
        PROCESSED_DIR / "api_football_fixtures.csv",
        fixture_rows,
        [
            "team",
            "api_football_team_id",
            "fixture_id",
            "date",
            "timestamp",
            "status",
            "league_id",
            "league",
            "season",
            "round",
            "home_team_id",
            "home_team",
            "away_team_id",
            "away_team",
            "opponent",
            "venue",
            "goals_for",
            "goals_against",
        ],
    )
    write_csv(
        PROCESSED_DIR / "api_football_fixture_statistics.csv",
        stats_rows,
        ["fixture_id", "date", "api_football_team_id", "team", "opponent", "stat", "raw_stat", "value"],
    )
    write_csv(
        PROCESSED_DIR / "api_football_team_match_stats.csv",
        team_stats_rows,
        [
            "team",
            "fixtures_with_stats",
            "avg_shots_on_goal",
            "avg_total_shots",
            "avg_fouls",
            "avg_corners",
            "avg_yellow_cards",
            "avg_red_cards",
            "avg_possession",
        ],
    )
    write_csv(PROCESSED_DIR / "api_football_coverage.csv", coverage_rows, ["metric", "value"])

    print(f"requests_used={budget.used}/{budget.limit}")
    print(f"teams_matched={coverage_rows[3]['value']}/{len(teams)}")
    print(f"fixtures={len(fixture_rows)}")
    print(f"stat_rows={len(stats_rows)}")
    print(f"teams_with_stats={len(team_stats_rows)}")


if __name__ == "__main__":
    main()
