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

CLIENT_MOCK_DB_PATH = Path('/Users/ljmartinez/antigravity/Baseball-Simulation-Client/data/mock_baseball_db.json')


def load_players_seed() -> list:
    """Loads players from mock_baseball_db.json if available, or returns standard seed list."""
    if CLIENT_MOCK_DB_PATH.exists():
        try:
            with open(CLIENT_MOCK_DB_PATH, 'r') as f:
                data = json.load(f)
            players = data.get('players', [])
            if players:
                return players
        except Exception as e:
            print(f'Warning: Failed to load from {CLIENT_MOCK_DB_PATH}: {e}')

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
    print(f'Seeding {len(raw_players)} players for season {season}...')

    team_name_map = {
        'NYY': 'New York Yankees',
        'NYM': 'New York Mets',
        'New York Yankees': 'New York Yankees',
        'New York Mets': 'New York Mets'
    }

    for p in raw_players:
        team_abbr = p.get('team', 'NYY')
        team_full = team_name_map.get(team_abbr, 'New York Yankees')

        vitals = {
            'age': p.get('age', 28),
            'experience': p.get('experience', 4),
            'height': p.get('height', '6-2'),
            'weight': p.get('weight', 215),
            'bats': p.get('bats', 'R'),
            'throws': p.get('throws', 'R'),
            'team': team_full,
        }

        # Convert ratings to list format
        raw_ratings = p.get('ratings', {})
        ratings_list = []
        if isinstance(raw_ratings, dict):
            for k, v in raw_ratings.items():
                cat_name = k.replace('_rating', '').replace('_', ' ').title()
                ratings_list.append({'category': cat_name, 'rating': int(v)})
                # Also include exact key
                ratings_list.append({'category': k, 'rating': int(v)})
        elif isinstance(raw_ratings, list):
            ratings_list = raw_ratings

        # Convert zones to list format
        zones_list = []
        raw_zones = p.get('zones', []) or p.get('hot_zones', [])
        if isinstance(raw_zones, dict):
            for z, slg in raw_zones.items():
                zones_list.append({'zone': z, 'slugging': float(slg)})
        elif isinstance(raw_zones, list):
            for item in raw_zones:
                if isinstance(item, dict):
                    zones_list.append({'zone': str(item.get('zone', 'heart')), 'slugging': float(item.get('slugging', 0.400))})

        # Pitch arsenal
        raw_arsenal = p.get('arsenal', [])
        pitch_arsenal = []
        for a in raw_arsenal:
            pitch_arsenal.append({
                'pitch': a.get('name', '4-Seam Fastball'),
                'name': a.get('name', '4-Seam Fastball'),
                'avg_velo_mph': a.get('velocity_mph', 95.0),
                'velocity_mph': a.get('velocity_mph', 95.0),
                'max_velo_mph': a.get('velocity_mph', 95.0) + 2.0,
                'avg_spin_rpm': a.get('spin_rpm', 2400),
                'spin_rpm': a.get('spin_rpm', 2400),
                'usage_pct': 0.35,
                'usage_pct_vs_rhb': 0.35,
                'usage_pct_vs_lhb': 0.35,
                'break_rating': a.get('break_rating', 85),
                'control_rating': a.get('control_rating', 80),
            })

        traits_list = []
        for t in p.get('traits', []):
            if isinstance(t, str):
                traits_list.append({'name': t, 'tier': 'Gold', 'description': t})
            elif isinstance(t, dict):
                traits_list.append(t)

        stats_list = p.get('stats', [{'season': season, 'avg': 0.280, 'hr': 25, 'rbi': 75, 'ops': 0.850}])

        pid, is_created = add_player(
            name=p.get('name', 'Player'),
            vitals=vitals,
            position=p.get('position', 'DH'),
            number=str(p.get('jersey_number', p.get('number', '99'))),
            stats=stats_list if isinstance(stats_list, list) else [stats_list],
            zones=zones_list,
            ratings=ratings_list,
            traits=traits_list,
            pitch_arsenal=pitch_arsenal,
            season=season
        )
        action = 'Added' if is_created else 'Updated'
        print(f'  + {action} [{pid}] {p.get("name")} ({p.get("position")}) -> {team_full}')

    print('Database seeding completed successfully.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fresh', action='store_true')
    parser.add_argument('--season', type=int, default=2026)
    args = parser.parse_args()
    run_seed(fresh=args.fresh, season=args.season)
