from __future__ import annotations

import csv
import unicodedata
from collections import defaultdict
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_SQUADS_PATH = (
    ROOT_DIR
    / "data"
    / "raw"
    / "Convocatorias_Oficiales"
    / "worldcup_2026_squads_groups_A_to_L.csv"
)
TRANSFERMARKT_PLAYERS_PATH = (
    ROOT_DIR / "data" / "raw" / "Football Data from Transfermarkt" / "players.csv"
)
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
SQUADS_OUTPUT_PATH = PROCESSED_DIR / "world_cup_2026_squads_enriched.csv"
TEAM_SUMMARY_OUTPUT_PATH = PROCESSED_DIR / "world_cup_2026_squad_summary.csv"


TEAM_ALIASES = {
    "Cabo Verde": "Cape Verde",
    "Democratic Republic of the Congo": "DR Congo",
    "Islamic Republic of Iran": "Iran",
    "Republic of Korea": "South Korea",
    "Türkiye": "Turkey",
    "United States of America": "United States",
    "Korea, South": "South Korea",
}


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(value.lower().replace(".", " ").replace("-", " ").split())


def compact_name_key(value: str) -> str:
    return normalize_text(value).replace(" ", "")


def clean_team(value: str) -> str:
    value = " ".join((value or "").replace("\xa0", " ").split()).strip()
    return TEAM_ALIASES.get(value, value)


def parse_int(value: str) -> int:
    if not value:
        return 0
    return int(float(value))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def build_player_index() -> dict[str, list[dict[str, str]]]:
    index: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(TRANSFERMARKT_PLAYERS_PATH):
        key = normalize_text(row["name"])
        if key:
            index[key].append(row)
            index[compact_name_key(row["name"])].append(row)
            parts = key.split()
            if len(parts) == 2:
                index[" ".join(reversed(parts))].append(row)
                index["".join(reversed(parts))].append(row)
            if len(parts) == 3:
                index[f"{parts[2]}{parts[0]}{parts[1]}"].append(row)
    return index


def choose_transfermarkt_player(
    candidates: list[dict[str, str]], team: str
) -> tuple[dict[str, str] | None, str]:
    if not candidates:
        return None, "unmatched"

    team_key = normalize_text(team)
    country_matches = [
        candidate
        for candidate in candidates
        if normalize_text(clean_team(candidate.get("country_of_citizenship", ""))) == team_key
        or normalize_text(clean_team(candidate.get("country_of_birth", ""))) == team_key
    ]
    pool = country_matches or candidates
    chosen = max(pool, key=lambda row: parse_int(row.get("market_value_in_eur", "")))
    return chosen, "country_match" if country_matches else "name_match"


def summarize_team(players: list[dict[str, object]]) -> dict[str, object]:
    values = sorted(
        [int(player["market_value_in_eur"]) for player in players if int(player["market_value_in_eur"]) > 0],
        reverse=True,
    )
    return {
        "group": players[0]["group"],
        "team": players[0]["team"],
        "players_count": len(players),
        "matched_players": sum(1 for player in players if player["match_status"] != "unmatched"),
        "squad_market_value": sum(values),
        "average_player_value": round(sum(values) / len(values), 2) if values else 0,
        "top_5_players_value": sum(values[:5]),
        "top_11_players_value": sum(values[:11]),
        "top_23_players_value": sum(values[:23]),
        "goalkeepers": sum(1 for player in players if player["position_group"] == "Goalkeepers"),
        "defenders": sum(1 for player in players if player["position_group"] == "Defenders"),
        "midfielders": sum(1 for player in players if "Midfielders" in str(player["position_group"])),
        "forwards": sum(1 for player in players if "Forwards" in str(player["position_group"])),
    }


def main() -> None:
    player_index = build_player_index()
    enriched_rows: list[dict[str, object]] = []

    for row in read_csv(RAW_SQUADS_PATH):
        team = clean_team(row["country"])
        candidates = player_index.get(normalize_text(row["player"]), [])
        if not candidates:
            candidates = player_index.get(compact_name_key(row["player"]), [])
        match, status = choose_transfermarkt_player(candidates, team)
        enriched_rows.append(
            {
                "group": row["group"],
                "team": team,
                "original_country": row["country"],
                "squad_status": row["squad_status"],
                "position_group": row["position_group"],
                "player_order_in_position": row["player_order_in_position"],
                "player": row["player"],
                "official_club": row["club"],
                "notes": row["notes"],
                "source_url": row["source_url"],
                "transfermarkt_player_id": match.get("player_id", "") if match else "",
                "transfermarkt_name": match.get("name", "") if match else "",
                "transfermarkt_club": match.get("current_club_name", "") if match else "",
                "country_of_citizenship": match.get("country_of_citizenship", "") if match else "",
                "position": match.get("position", "") if match else "",
                "sub_position": match.get("sub_position", "") if match else "",
                "foot": match.get("foot", "") if match else "",
                "height_in_cm": match.get("height_in_cm", "") if match else "",
                "market_value_in_eur": parse_int(match.get("market_value_in_eur", "")) if match else 0,
                "highest_market_value_in_eur": parse_int(match.get("highest_market_value_in_eur", "")) if match else 0,
                "international_caps": parse_int(match.get("international_caps", "")) if match else 0,
                "international_goals": parse_int(match.get("international_goals", "")) if match else 0,
                "match_status": status,
            }
        )

    by_team: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in enriched_rows:
        by_team[str(row["team"])].append(row)

    summary_rows = [summarize_team(rows) for rows in by_team.values()]

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with SQUADS_OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(enriched_rows[0].keys()))
        writer.writeheader()
        writer.writerows(enriched_rows)

    with TEAM_SUMMARY_OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(sorted(summary_rows, key=lambda row: (str(row["group"]), str(row["team"]))))

    print(f"squads={len(enriched_rows)}")
    print(f"teams={len(summary_rows)}")
    print(f"matched={sum(1 for row in enriched_rows if row['match_status'] != 'unmatched')}")
    print(f"saved={SQUADS_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
