from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.thesportsdb_service import (  # noqa: E402
    TheSportsDBClient,
    TheSportsDBError,
)


PROCESSED_DIR = ROOT_DIR / "data" / "processed"
FIXTURES_PATH = PROCESSED_DIR / "world_cup_2026_fixtures.csv"
API_CACHE_DIR = ROOT_DIR / "data" / "api_cache" / "thesportsdb"

TEAM_ALIASES = {
    "Bosnia and Herzegovina": ["Bosnia-Herzegovina", "Bosnia"],
    "Cape Verde": ["Cabo Verde", "Cape Verde Islands"],
    "Côte d'Ivoire": ["Ivory Coast", "Cote d'Ivoire"],
    "Czechia": ["Czech Republic"],
    "DR Congo": ["Congo DR", "Democratic Republic of Congo"],
    "South Korea": ["Korea Republic", "Republic of Korea"],
    "Turkey": ["Türkiye", "Turkiye"],
    "United States": ["USA", "United States of America"],
}

STAT_ALIASES = {
    "ball possession": "possession",
    "possession": "possession",
    "total shots": "shots",
    "shots": "shots",
    "shots on target": "shots_on_target",
    "shots on goal": "shots_on_target",
    "corners": "corners",
    "corner kicks": "corners",
    "fouls": "fouls",
    "yellow cards": "yellow_cards",
    "red cards": "red_cards",
}

RECENT_STAT_COLUMNS = [
    "team",
    "events_with_stats",
    "avg_possession_last_available",
    "avg_shots_last_available",
    "avg_shots_on_target_last_available",
    "avg_corners_last_available",
    "avg_fouls_last_available",
    "avg_yellow_cards_last_available",
    "avg_red_cards_last_available",
]


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return value or "unknown"


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(value.lower().replace("-", " ").replace(".", " ").split())


def parse_int(value: Any) -> int | None:
    if value in ("", None):
        return None
    try:
        return int(float(str(value).replace("%", "").strip()))
    except ValueError:
        return None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def world_cup_teams() -> list[str]:
    rows = read_csv(FIXTURES_PATH)
    teams = {row["home_team"] for row in rows} | {row["away_team"] for row in rows}
    return sorted(team for team in teams if team)


def search_names(team: str) -> list[str]:
    return [team, *TEAM_ALIASES.get(team, [])]


def payload_items(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    data = payload.get("data") or {}
    items = data.get(key)
    return items if isinstance(items, list) else []


def choose_team(team: str, payloads: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    candidates = []
    team_key = normalize_text(team)
    alias_keys = {normalize_text(name) for name in search_names(team)}

    for payload in payloads:
        candidates.extend(payload_items(payload, "teams"))

    if not candidates:
        return None, "unmatched"

    for candidate in candidates:
        name = normalize_text(candidate.get("strTeam", ""))
        alternate = normalize_text(candidate.get("strAlternate", ""))
        if name == team_key or name in alias_keys or team_key in alternate:
            return candidate, "exact"

    national_candidates = [
        candidate
        for candidate in candidates
        if normalize_text(candidate.get("strSport", "")) == "soccer"
        and normalize_text(candidate.get("strLeague", "")).startswith("international")
    ]
    if national_candidates:
        return national_candidates[0], "fallback_international"
    return candidates[0], "fallback_first"


def score_for_team(event: dict[str, Any], team_id: str, team: str) -> tuple[int | None, int | None, str, str]:
    home_id = str(event.get("idHomeTeam", ""))
    away_id = str(event.get("idAwayTeam", ""))
    home_team = str(event.get("strHomeTeam", ""))
    away_team = str(event.get("strAwayTeam", ""))
    home_score = parse_int(event.get("intHomeScore"))
    away_score = parse_int(event.get("intAwayScore"))
    is_home = home_id == team_id or normalize_text(home_team) == normalize_text(team)

    if home_score is None or away_score is None:
        return None, None, "", away_team if is_home else home_team
    if is_home:
        return home_score, away_score, "home", away_team
    return away_score, home_score, "away", home_team


def result_label(goals_for: int | None, goals_against: int | None) -> str:
    if goals_for is None or goals_against is None:
        return ""
    if goals_for > goals_against:
        return "win"
    if goals_for == goals_against:
        return "draw"
    return "loss"


def flatten_team_mapping(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return rows


def flatten_players(team: str, team_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for player in payload_items(payload, "player"):
        rows.append(
            {
                "team": team,
                "thesportsdb_team_id": team_id,
                "player_id": player.get("idPlayer", ""),
                "player": player.get("strPlayer", ""),
                "position": player.get("strPosition", ""),
                "nationality": player.get("strNationality", ""),
                "date_born": player.get("dateBorn", ""),
                "birth_location": player.get("strBirthLocation", ""),
                "height": player.get("strHeight", ""),
                "weight": player.get("strWeight", ""),
                "thumb": player.get("strThumb", ""),
                "cutout": player.get("strCutout", ""),
                "status": player.get("strStatus", ""),
            }
        )
    return rows


def flatten_events(team: str, team_id: str, payload: dict[str, Any], event_type: str) -> list[dict[str, Any]]:
    rows = []
    for event in payload_items(payload, "results" if event_type == "last" else "events"):
        goals_for, goals_against, venue, opponent = score_for_team(event, team_id, team)
        rows.append(
            {
                "team": team,
                "thesportsdb_team_id": team_id,
                "event_type": event_type,
                "event_id": event.get("idEvent", ""),
                "date": event.get("dateEvent", ""),
                "time": event.get("strTime", ""),
                "competition": event.get("strLeague", ""),
                "season": event.get("strSeason", ""),
                "round": event.get("intRound", ""),
                "home_team": event.get("strHomeTeam", ""),
                "away_team": event.get("strAwayTeam", ""),
                "opponent": opponent,
                "venue": venue,
                "goals_for": "" if goals_for is None else goals_for,
                "goals_against": "" if goals_against is None else goals_against,
                "result": result_label(goals_for, goals_against),
            }
        )
    return rows


def recent_form(team: str, events: list[dict[str, Any]], max_matches: int = 5) -> dict[str, Any]:
    played = [
        row
        for row in events
        if row["team"] == team and row["event_type"] == "last" and row["result"]
    ][:max_matches]
    goals_for = sum(int(row["goals_for"]) for row in played)
    goals_against = sum(int(row["goals_against"]) for row in played)
    wins = sum(1 for row in played if row["result"] == "win")
    draws = sum(1 for row in played if row["result"] == "draw")
    losses = sum(1 for row in played if row["result"] == "loss")
    points = wins * 3 + draws
    count = len(played)

    return {
        "team": team,
        "matches_available": count,
        "wins_last_available": wins,
        "draws_last_available": draws,
        "losses_last_available": losses,
        "points_last_available": points,
        "goals_for_last_available": goals_for,
        "goals_against_last_available": goals_against,
        "goal_difference_last_available": goals_for - goals_against,
        "avg_goals_for_last_available": round(goals_for / count, 3) if count else 0,
        "avg_goals_against_last_available": round(goals_against / count, 3) if count else 0,
    }


def stat_name(value: str) -> str:
    return STAT_ALIASES.get(normalize_text(value), slugify(value))


def flatten_event_stats(payload: dict[str, Any], event_lookup: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for stat in payload_items(payload, "eventstats"):
        event_id = str(stat.get("idEvent", ""))
        event = event_lookup.get(event_id, {})
        rows.append(
            {
                "event_id": event_id,
                "date": event.get("date", ""),
                "home_team": event.get("home_team", ""),
                "away_team": event.get("away_team", ""),
                "stat": stat_name(str(stat.get("strStat", ""))),
                "raw_stat": stat.get("strStat", ""),
                "home_value": stat.get("intHome", ""),
                "away_value": stat.get("intAway", ""),
            }
        )
    return rows


def summarize_recent_stats(stats_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_team: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    events_seen: dict[str, set[str]] = defaultdict(set)

    for row in stats_rows:
        home = row["home_team"]
        away = row["away_team"]
        stat = row["stat"]
        if stat not in {"possession", "shots", "shots_on_target", "corners", "fouls", "yellow_cards", "red_cards"}:
            continue
        home_value = parse_int(row["home_value"])
        away_value = parse_int(row["away_value"])
        if home and home_value is not None:
            by_team[home][stat].append(home_value)
            events_seen[home].add(row["event_id"])
        if away and away_value is not None:
            by_team[away][stat].append(away_value)
            events_seen[away].add(row["event_id"])

    rows = []
    for team, stats in sorted(by_team.items()):
        output = {"team": team, "events_with_stats": len(events_seen[team])}
        for column in RECENT_STAT_COLUMNS[2:]:
            metric = column.removeprefix("avg_").removesuffix("_last_available")
            values = stats.get(metric, [])
            output[column] = round(sum(values) / len(values), 3) if values else 0
        rows.append(output)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync TheSportsDB V1 data for World Cup teams.")
    parser.add_argument("--from-cache", action="store_true", help="Regenerate CSVs from cached JSON.")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds.")
    parser.add_argument("--request-delay", type=float, default=0.35, help="Delay between API requests.")
    parser.add_argument("--limit", type=int, default=0, help="Limit teams for quick coverage tests.")
    parser.add_argument(
        "--include-event-enrichment",
        action="store_true",
        help="Also fetch event details, stats, lineups and timeline for recent events.",
    )
    parser.add_argument(
        "--max-events-per-team",
        type=int,
        default=5,
        help="Maximum recent events per team to enrich when --include-event-enrichment is enabled.",
    )
    return parser.parse_args()


def cached_or_fetch(
    path: Path,
    fetch,
    from_cache: bool,
) -> dict[str, Any]:
    if path.exists():
        return read_json(path)
    if from_cache:
        return {"data": {}}
    payload = fetch()
    write_json(path, payload)
    return payload


def main() -> None:
    args = parse_args()
    client = TheSportsDBClient(timeout=args.timeout, request_delay=args.request_delay)
    teams = world_cup_teams()
    if args.limit > 0:
        teams = teams[: args.limit]

    mapping_rows: list[dict[str, Any]] = []
    players_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    event_stats_rows: list[dict[str, Any]] = []
    event_lookup: dict[str, dict[str, Any]] = {}
    event_ids_to_enrich: set[str] = set()

    for index, team in enumerate(teams, start=1):
        print(f"[{index}/{len(teams)}] {team}", flush=True)
        team_slug = slugify(team)
        search_payloads = []
        for search_name in search_names(team):
            search_path = API_CACHE_DIR / "teams" / team_slug / f"search_{slugify(search_name)}.json"
            payload = cached_or_fetch(
                search_path,
                lambda search_name=search_name: client.search_team(search_name),
                args.from_cache,
            )
            search_payloads.append(payload)

        chosen, match_status = choose_team(team, search_payloads)
        team_id = str(chosen.get("idTeam", "")) if chosen else ""
        mapping_rows.append(
            {
                "team": team,
                "thesportsdb_team_id": team_id,
                "thesportsdb_team": chosen.get("strTeam", "") if chosen else "",
                "country": chosen.get("strCountry", "") if chosen else "",
                "league": chosen.get("strLeague", "") if chosen else "",
                "stadium": chosen.get("strStadium", "") if chosen else "",
                "badge": chosen.get("strBadge", "") if chosen else "",
                "logo": chosen.get("strLogo", "") if chosen else "",
                "banner": chosen.get("strBanner", "") if chosen else "",
                "match_status": match_status,
            }
        )
        if not team_id:
            continue

        requests = {
            "lookup_team": lambda: client.lookup_team(team_id),
            "players": lambda: client.lookup_all_players(team_id),
            "last_events": lambda: client.last_events(team_id),
            "next_events": lambda: client.next_events(team_id),
        }

        payloads = {}
        for name, fetch in requests.items():
            path = API_CACHE_DIR / name / f"{team_slug}.json"
            try:
                payloads[name] = cached_or_fetch(path, fetch, args.from_cache)
            except TheSportsDBError as error:
                print(f"warning: {team} {name}: {error}")
                payloads[name] = {"data": {}}
                if not args.from_cache:
                    write_json(path, payloads[name])

        players_rows.extend(flatten_players(team, team_id, payloads["players"]))
        last_events = flatten_events(team, team_id, payloads["last_events"], "last")
        next_events = flatten_events(team, team_id, payloads["next_events"], "next")
        event_rows.extend(last_events)
        event_rows.extend(next_events)

        for event in last_events[: args.max_events_per_team]:
            event_id = str(event["event_id"])
            if event_id:
                event_lookup[event_id] = event
                event_ids_to_enrich.add(event_id)

    if args.include_event_enrichment:
        for event_id in sorted(event_ids_to_enrich):
            for name, fetch in {
                "event_details": lambda event_id=event_id: client.lookup_event(event_id),
                "event_stats": lambda event_id=event_id: client.lookup_event_stats(event_id),
                "event_lineups": lambda event_id=event_id: client.lookup_lineup(event_id),
                "event_timeline": lambda event_id=event_id: client.lookup_timeline(event_id),
            }.items():
                path = API_CACHE_DIR / name / f"{event_id}.json"
                try:
                    payload = cached_or_fetch(path, fetch, args.from_cache)
                except TheSportsDBError as error:
                    print(f"warning: event {event_id} {name}: {error}")
                    payload = {"data": {}}
                    if not args.from_cache:
                        write_json(path, payload)

                if name == "event_stats":
                    event_stats_rows.extend(flatten_event_stats(payload, event_lookup))

    recent_form_rows = [recent_form(team, event_rows) for team in teams]
    coverage_rows = [
        {
            "metric": "teams_total",
            "value": len(teams),
        },
        {
            "metric": "teams_matched",
            "value": sum(1 for row in mapping_rows if row["thesportsdb_team_id"]),
        },
        {
            "metric": "players_rows",
            "value": len(players_rows),
        },
        {
            "metric": "last_event_rows",
            "value": sum(1 for row in event_rows if row["event_type"] == "last"),
        },
        {
            "metric": "next_event_rows",
            "value": sum(1 for row in event_rows if row["event_type"] == "next"),
        },
        {
            "metric": "event_stats_rows",
            "value": len(event_stats_rows),
        },
    ]

    write_csv(
        PROCESSED_DIR / "thesportsdb_team_mapping.csv",
        flatten_team_mapping(mapping_rows),
        ["team", "thesportsdb_team_id", "thesportsdb_team", "country", "league", "stadium", "badge", "logo", "banner", "match_status"],
    )
    write_csv(
        PROCESSED_DIR / "thesportsdb_players.csv",
        players_rows,
        ["team", "thesportsdb_team_id", "player_id", "player", "position", "nationality", "date_born", "birth_location", "height", "weight", "thumb", "cutout", "status"],
    )
    write_csv(
        PROCESSED_DIR / "thesportsdb_events.csv",
        event_rows,
        ["team", "thesportsdb_team_id", "event_type", "event_id", "date", "time", "competition", "season", "round", "home_team", "away_team", "opponent", "venue", "goals_for", "goals_against", "result"],
    )
    write_csv(
        PROCESSED_DIR / "thesportsdb_recent_form.csv",
        recent_form_rows,
        ["team", "matches_available", "wins_last_available", "draws_last_available", "losses_last_available", "points_last_available", "goals_for_last_available", "goals_against_last_available", "goal_difference_last_available", "avg_goals_for_last_available", "avg_goals_against_last_available"],
    )
    write_csv(PROCESSED_DIR / "thesportsdb_coverage.csv", coverage_rows, ["metric", "value"])

    if event_stats_rows:
        write_csv(
            PROCESSED_DIR / "thesportsdb_event_stats.csv",
            event_stats_rows,
            ["event_id", "date", "home_team", "away_team", "stat", "raw_stat", "home_value", "away_value"],
        )
        write_csv(
            PROCESSED_DIR / "thesportsdb_recent_match_stats.csv",
            summarize_recent_stats(event_stats_rows),
            RECENT_STAT_COLUMNS,
        )

    print(f"teams={len(teams)}")
    print(f"matched={sum(1 for row in mapping_rows if row['thesportsdb_team_id'])}")
    print(f"players={len(players_rows)}")
    print(f"events={len(event_rows)}")
    print(f"event_stats={len(event_stats_rows)}")
    print(f"saved={PROCESSED_DIR / 'thesportsdb_recent_form.csv'}")


if __name__ == "__main__":
    main()
