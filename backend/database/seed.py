"""
MLB Database Seeder.
Initializes SQLite schema and populates test rosters for the New York Yankees
and New York Mets with complete Statcast ratings, pitch arsenals, and trait profiles.
"""

import argparse
import json
from pathlib import Path
import sys

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database.db import DB_PATH, add_player, init_db

LEAGUE_AVG_SLG = 0.400

SEED_DATA_PATH = ROOT_DIR / 'backend' / 'database' / 'seed_data.json'


def load_players_seed() -> list:
    """Loads authoritative players from seed_data.json."""
    if SEED_DATA_PATH.exists():
        try:
            with open(SEED_DATA_PATH, 'r') as f:
                data = json.load(f)
            players = data.get('players', [])
            if players:
                return players
        except Exception as e:
            print(f'Warning: Failed to load from {SEED_DATA_PATH}: {e}')

    return []


def reset_database() -> None:
    """Removes existing SQLite binary and WAL files."""
    for ext in ['', '-wal', '-shm', '-journal']:
        target = Path(f'{DB_PATH}{ext}')
        if target.exists():
            target.unlink()
            print(f'Removed: {target.name}')


def run_seed(fresh: bool = False, season: int = 2026) -> None:
    if fresh:
        print('Resetting database...')
        reset_database()

    print('Initializing database schema...')
    init_db()

    raw_players = load_players_seed()
    if not raw_players:
        raise RuntimeError(
            f'No player seed data found at {SEED_DATA_PATH}. '
            'Ensure the seed data file (backend/database/seed_data.json) is present.'
        )
    print(f'Seeding {len(raw_players)} players for season {season}...')

    team_name_map = {
        'NYY': 'New York Yankees',
        'NYM': 'New York Mets',
        'New York Yankees': 'New York Yankees',
        'New York Mets': 'New York Mets'
    }

    NUMERIC_ZONE_MAP = {
        1: 'upper-in',    2: 'upper-middle', 3: 'upper-away',
        4: 'middle-in',   5: 'heart',        6: 'middle-away',
        7: 'lower-in',    8: 'lower-middle', 9: 'lower-away',
    }

    batting_order_counts = {}

    for p in raw_players:
        team_abbr = p.get('team', 'NYY')
        team_full = team_name_map.get(team_abbr, 'New York Yankees')
        pos = p.get('position', 'DH')
        is_pitcher = pos in ('P', 'SP', 'RP', 'CP') or len(p.get('arsenal', [])) > 0
        role = p.get('role') or ('pitcher' if is_pitcher else 'batter')

        if not is_pitcher:
            order = batting_order_counts.get(team_full, 0) + 1
            batting_order_counts[team_full] = order
            batting_order = order
        else:
            batting_order = None

        jersey_num = p.get('jersey_number', p.get('number', 99))
        jersey_num_int = int(jersey_num) if str(jersey_num).isdigit() else 99

        motion_bio = p.get('motion_bio') or {}
        raw_ratings = p.get('ratings', {})
        arsenal = p.get('arsenal', [])
        season_stats = p.get('season_stats', {})
        live_game_stats = p.get('live_game_stats', {})
        throws = p.get('throws', 'R')
        bats = p.get('bats', 'R')

        # Convert hot_zones / zones for batters
        zones_list = []
        raw_zones = p.get('hot_zones') or p.get('zones') or []
        if isinstance(raw_zones, list):
            for item in raw_zones:
                if not isinstance(item, dict):
                    continue
                raw_name = item.get('name') or item.get('zone')
                if isinstance(raw_name, int) and raw_name in NUMERIC_ZONE_MAP:
                    zone_name = NUMERIC_ZONE_MAP[raw_name]
                elif str(raw_name).isdigit() and int(raw_name) in NUMERIC_ZONE_MAP:
                    zone_name = NUMERIC_ZONE_MAP[int(raw_name)]
                else:
                    zone_name = str(raw_name or 'heart')

                slugging = item.get('slugging', item.get('slg'))
                if slugging is None:
                    multiplier = item.get('slg_multiplier', item.get('multiplier'))
                    if multiplier is not None:
                        try:
                            slugging = LEAGUE_AVG_SLG * float(multiplier)
                        except (TypeError, ValueError):
                            slugging = None
                if slugging is None:
                    slugging = LEAGUE_AVG_SLG

                zone_entry = dict(item)
                zone_entry['zone'] = zone_name
                zone_entry['slugging'] = round(float(slugging), 3)
                zones_list.append(zone_entry)
        elif isinstance(raw_zones, dict):
            for z, slg in raw_zones.items():
                value = float(slg)
                if value > 1.0:
                    value = LEAGUE_AVG_SLG * value
                zones_list.append({'zone': z, 'slugging': round(value, 3)})

        traits_list = p.get('traits', [])

        pid, is_created = add_player(
            id=p.get('id'),
            name=p.get('name', 'Player'),
            team=team_abbr,
            team_name=team_full,
            position=pos,
            jersey_number=jersey_num_int,
            number=str(jersey_num_int),
            role=role,
            throws=throws,
            bats=bats,
            motion_bio=motion_bio,
            ratings=raw_ratings,
            arsenal=arsenal,
            pitch_arsenal=arsenal,
            season_stats=season_stats,
            live_game_stats=live_game_stats,
            hot_zones=zones_list,
            zones=zones_list,
            traits=traits_list,
            batting_order=batting_order,
            roster_status='active',
            season=season,
        )
        action = 'Added' if is_created else 'Updated'
        order_str = f' [#{batting_order}]' if batting_order else ''
        print(f'  + {action} [{pid}] #{jersey_num_int} {p.get("name")} ({pos}){order_str} -> {team_full} ({role})')

    print('Database seeding completed successfully.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fresh', action='store_true')
    parser.add_argument('--season', type=int, default=2026)
    args = parser.parse_args()
    run_seed(fresh=args.fresh, season=args.season)
