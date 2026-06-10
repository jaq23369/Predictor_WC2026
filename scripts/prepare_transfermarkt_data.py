from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import median


ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT_DIR / "data" / "raw" / "Football Data from Transfermarkt"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

NATIONAL_TEAMS_PATH = RAW_DIR / "national_teams.csv"
PLAYERS_PATH = RAW_DIR / "players.csv"
OUTPUT_PATH = PROCESSED_DIR / "transfermarkt_national_team_values.csv"


TEAM_ALIASES = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Cape Verde Islands": "Cape Verde",
    "Congo DR": "DR Congo",
    "Czech Republic": "Czechia",
    "Ivory Coast": "Côte d'Ivoire",
    "Korea Republic": "South Korea",
    "South Korea": "South Korea",
    "Turkiye": "Turkey",
    "Türkiye": "Turkey",
    "United States": "United States",
}


def clean_name(value: str) -> str:
    value = " ".join(value.replace("\xa0", " ").split()).strip()
    return TEAM_ALIASES.get(value, value)


def parse_int(value: str) -> int:
    if not value:
        return 0
    return int(float(value))


def parse_float(value: str) -> float:
    if not value:
        return 0.0
    return float(value)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def player_aggregates() -> dict[str, dict[str, object]]:
    values_by_team: dict[str, list[int]] = defaultdict(list)
    caps_by_team: dict[str, list[int]] = defaultdict(list)
    goals_by_team: dict[str, list[int]] = defaultdict(list)

    with PLAYERS_PATH.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            team_id = row.get("current_national_team_id") or ""
            if not team_id:
                continue

            market_value = parse_int(row.get("market_value_in_eur", ""))
            if market_value > 0:
                values_by_team[team_id].append(market_value)

            caps = parse_int(row.get("international_caps", ""))
            goals = parse_int(row.get("international_goals", ""))
            if caps > 0:
                caps_by_team[team_id].append(caps)
            if goals > 0:
                goals_by_team[team_id].append(goals)

    aggregates: dict[str, dict[str, object]] = {}
    for team_id, values in values_by_team.items():
        sorted_values = sorted(values, reverse=True)
        aggregates[team_id] = {
            "players_with_market_value": len(sorted_values),
            "players_market_value_sum": sum(sorted_values),
            "players_market_value_avg": round(sum(sorted_values) / len(sorted_values), 2),
            "players_market_value_median": int(median(sorted_values)),
            "top_5_players_value": sum(sorted_values[:5]),
            "top_11_players_value": sum(sorted_values[:11]),
            "top_23_players_value": sum(sorted_values[:23]),
            "total_international_caps": sum(caps_by_team.get(team_id, [])),
            "total_international_goals": sum(goals_by_team.get(team_id, [])),
        }

    return aggregates


def main() -> None:
    aggregates = player_aggregates()
    rows: list[dict[str, object]] = []

    for row in read_csv(NATIONAL_TEAMS_PATH):
        team_id = row["national_team_id"]
        aggregate = aggregates.get(team_id, {})
        rows.append(
            {
                "team": clean_name(row["name"]),
                "transfermarkt_name": row["name"],
                "national_team_id": team_id,
                "country_name": row["country_name"],
                "country_code": row["country_code"],
                "confederation": row["confederation"],
                "squad_size": parse_int(row["squad_size"]),
                "average_age": parse_float(row["average_age"]),
                "foreigners_number": parse_int(row["foreigners_number"]),
                "foreigners_percentage": parse_float(row["foreigners_percentage"]),
                "total_market_value": parse_int(row["total_market_value"]),
                "fifa_ranking_transfermarkt": parse_int(row["fifa_ranking"]),
                "players_with_market_value": aggregate.get("players_with_market_value", 0),
                "players_market_value_sum": aggregate.get("players_market_value_sum", 0),
                "players_market_value_avg": aggregate.get("players_market_value_avg", 0),
                "players_market_value_median": aggregate.get("players_market_value_median", 0),
                "top_5_players_value": aggregate.get("top_5_players_value", 0),
                "top_11_players_value": aggregate.get("top_11_players_value", 0),
                "top_23_players_value": aggregate.get("top_23_players_value", 0),
                "total_international_caps": aggregate.get("total_international_caps", 0),
                "total_international_goals": aggregate.get("total_international_goals", 0),
                "url": row["url"],
            }
        )

    fieldnames = list(rows[0].keys())
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda item: str(item["team"])))

    print(f"saved={OUTPUT_PATH}")
    print(f"rows={len(rows)}")


if __name__ == "__main__":
    main()
