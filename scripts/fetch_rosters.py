#!/usr/bin/env python3
"""
MLB Rosters Fetcher.

Fetches the latest official 40-man rosters from the MLB Stats API
for the New York Yankees (team ID 147) and New York Mets (team ID 121),
hydrating full biographical data, physical vitals, and season stats.
Saves output to backend/database/latest_rosters.json.
"""

import argparse
import datetime
import json
from pathlib import Path
import sys
import urllib.request
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT_DIR / "backend" / "database" / "latest_rosters.json"

TEAMS = [
    {"id": 147, "name": "New York Yankees", "abbr": "NYY"},
    {"id": 121, "name": "New York Mets", "abbr": "NYM"},
]


def fetch_team_roster(team_id: int, roster_type: str = "40Man") -> List[Dict[str, Any]]:
    """Fetches roster with hydrated person and season stat data from MLB Stats API."""
    url = (
        f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster"
        f"?rosterType={roster_type}&hydrate=person(stats(type=season))"
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MLB-Baseball-Simulation/1.0 (Mozilla/5.0 compatible)"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("roster", [])


def process_player(raw_item: Dict[str, Any], team_abbr: str) -> Dict[str, Any]:
    """Extracts and normalizes player vitals, positional data, and stats."""
    person = raw_item.get("person", {})
    pos = raw_item.get("position", {})
    status = raw_item.get("status", {})

    bat_side = person.get("batSide", {}).get("code", "R")
    pitch_hand = person.get("pitchHand", {}).get("code", "R")
    pos_type = pos.get("type", "Unknown")
    pos_abbr = pos.get("abbreviation", "DH")
    is_pitcher = pos_type == "Pitcher" or pos_abbr in ("P", "SP", "RP", "CP")

    # Extract latest season stats if available
    stat_splits = {}
    stats_list = person.get("stats", [])
    if stats_list:
        for st in stats_list:
            splits = st.get("splits", [])
            if splits:
                stat_splits = splits[-1].get("stat", {})
                break

    jersey_str = raw_item.get("jerseyNumber") or person.get("primaryNumber") or "--"

    return {
        "mlb_id": person.get("id"),
        "name": person.get("fullName", "Unknown Player"),
        "team": team_abbr,
        "jersey_number": jersey_str,
        "position": pos_abbr,
        "position_name": pos.get("name", pos_abbr),
        "position_type": pos_type,
        "is_pitcher": is_pitcher,
        "bats": bat_side,
        "throws": pitch_hand,
        "height": person.get("height", ""),
        "weight": person.get("weight", 0),
        "current_age": person.get("currentAge"),
        "strike_zone_top": person.get("strikeZoneTop"),
        "strike_zone_bottom": person.get("strikeZoneBottom"),
        "status": status.get("description", "Active"),
        "season_stats": stat_splits,
    }


def fetch_and_save_rosters(output_path: Path = OUTPUT_FILE) -> Dict[str, Any]:
    """Fetches rosters for both New York teams and writes to JSON."""
    result = {
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": "https://statsapi.mlb.com",
        "teams": {},
    }

    for team in TEAMS:
        t_id = team["id"]
        t_abbr = team["abbr"]
        t_name = team["name"]
        print(f"Fetching official roster for {t_name} ({t_abbr})...")

        raw_roster = fetch_team_roster(t_id)
        processed_players = [process_player(p, t_abbr) for p in raw_roster]

        pitchers = [p for p in processed_players if p["is_pitcher"]]
        position_players = [p for p in processed_players if not p["is_pitcher"]]

        result["teams"][t_abbr] = {
            "team_id": t_id,
            "team_name": t_name,
            "total_players": len(processed_players),
            "pitchers_count": len(pitchers),
            "position_players_count": len(position_players),
            "pitchers": sorted(pitchers, key=lambda x: (x["jersey_number"] == "--", x["name"])),
            "position_players": sorted(position_players, key=lambda x: (x["position"], x["name"])),
            "all_players": processed_players,
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"\nSuccessfully saved updated rosters to {output_path}")
    return result


def print_roster_summary(data: Dict[str, Any]) -> None:
    """Formats and prints summary tables for both rosters."""
    for abbr, team_info in data.get("teams", {}).items():
        print(f"\n{'='*70}")
        print(f"  ⚾ {team_info['team_name']} ({abbr}) — 40-Man Roster ({team_info['total_players']} players)")
        print(f"{'='*70}")

        print(f"\n--- POSITION PLAYERS ({team_info['position_players_count']}) ---")
        print(f"{'#':<4} {'Name':<24} {'Pos':<5} {'B/T':<5} {'Age':<5} {'Key Stats'}")
        print(f"{'-'*4} {'-'*24} {'-'*5} {'-'*5} {'-'*5} {'-'*25}")
        for p in team_info["position_players"]:
            num = p["jersey_number"]
            bt = f"{p['bats']}/{p['throws']}"
            age = str(p['current_age']) if p['current_age'] else "--"
            stats = p.get("season_stats", {})
            stat_summary = ""
            if stats:
                avg = stats.get("avg", ".---")
                hr = stats.get("homeRuns", 0)
                rbi = stats.get("rbi", 0)
                ops = stats.get("ops", ".---")
                stat_summary = f"AVG: {avg} | HR: {hr} | RBI: {rbi} | OPS: {ops}"
            print(f"{num:<4} {p['name']:<24} {p['position']:<5} {bt:<5} {age:<5} {stat_summary}")

        print(f"\n--- PITCHERS ({team_info['pitchers_count']}) ---")
        print(f"{'#':<4} {'Name':<24} {'Pos':<5} {'Throws':<7} {'Age':<5} {'Key Stats'}")
        print(f"{'-'*4} {'-'*24} {'-'*5} {'-'*7} {'-'*5} {'-'*25}")
        for p in team_info["pitchers"]:
            num = p["jersey_number"]
            thr = f"Throws {p['throws']}"
            age = str(p['current_age']) if p['current_age'] else "--"
            stats = p.get("season_stats", {})
            stat_summary = ""
            if stats:
                era = stats.get("era", "-.--")
                w = stats.get("wins", 0)
                l = stats.get("losses", 0)
                so = stats.get("strikeOuts", 0)
                whip = stats.get("whip", "-.--")
                ip = stats.get("inningsPitched", "-.-")
                stat_summary = f"W-L: {w}-{l} | ERA: {era} | WHIP: {whip} | K: {so} ({ip} IP)"
            print(f"{num:<4} {p['name']:<24} {p['position']:<5} {thr:<7} {age:<5} {stat_summary}")


def main():
    parser = argparse.ArgumentParser(description="Fetch latest NYY and NYM MLB rosters.")
    parser.add_argument("--output", type=str, default=str(OUTPUT_FILE), help="Output JSON path")
    args = parser.parse_args()

    data = fetch_and_save_rosters(Path(args.output))
    print_roster_summary(data)


if __name__ == "__main__":
    main()

