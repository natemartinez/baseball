#!/usr/bin/env python3
"""
Prints a plate-discipline calibration report from a seeded game sample.

Usage:
    python scripts/swing_calibration_report.py
"""

from collections import defaultdict
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database.db import get_player
from backend.engine.game_engine import GameEngine


def _game(seed):
    pitcher = get_player(1)
    batter = get_player(4)
    roster = {
        'name': 'Calibration',
        'position_players': [batter],
        'pitchers': {'starters': [pitcher], 'bullpen': []},
    }
    return GameEngine(roster, roster, 'Home', 'Away', seed=seed)


def _collect(target=8000, max_games=60):
    rows = []
    seed = 2026
    games = 0
    while len(rows) < target and games < max_games:
        game = _game(seed)
        for _ in range(3000):
            if game.game_over:
                break
            thrown = game.throw_pitch()
            if thrown.get('status') != 'success':
                break
            pending = game.orchestrator.pending
            if pending is None:
                break
            resolved = game.resolve_pitch()
            if resolved.get('status') != 'success':
                break
            details = resolved['pitch_details']
            rows.append({
                'balls': pending.balls,
                'strikes': pending.strikes,
                'is_strike': pending.is_strike,
                'swing': details['batter_decision'] == 'SWING',
                'zone_category': pending.zone_category,
            })
        seed += 1
        games += 1
    return rows


def _rate(rows, predicate):
    selected = [row for row in rows if predicate(row)]
    return (sum(1 for row in selected if row['swing']) / len(selected), len(selected)) if selected else (0.0, 0)


def main():
    rows = _collect()
    print(f'Plate discipline report — {len(rows)} pitches')
    checks = [
        ('Overall swing', lambda row: True),
        ('In-zone swing', lambda row: row['is_strike']),
        ('Chase (out-of-zone)', lambda row: not row['is_strike']),
        ('First pitch', lambda row: row['balls'] == 0 and row['strikes'] == 0),
        ('3-0', lambda row: row['balls'] == 3 and row['strikes'] == 0),
        ('Two-strike chase', lambda row: row['strikes'] == 2 and not row['is_strike']),
    ]
    for label, predicate in checks:
        value, count = _rate(rows, predicate)
        print(f'{label:22} {value * 100:5.1f}%  (n={count})')

    print('\nBy count:')
    by_count = defaultdict(list)
    for row in rows:
        by_count[(row['balls'], row['strikes'])].append(row)
    for count in sorted(by_count):
        value, count_n = _rate(by_count[count], lambda row: True)
        if count_n >= 20:
            print(f'  {count[0]}-{count[1]}: {value * 100:5.1f}%  (n={count_n})')

    print('\nBy zone category:')
    by_zone = defaultdict(list)
    for row in rows:
        by_zone[row['zone_category']].append(row)
    for zone in sorted(by_zone):
        value, count_n = _rate(by_zone[zone], lambda row: True)
        print(f'  {zone:6}: {value * 100:5.1f}%  (n={count_n})')


if __name__ == '__main__':
    main()
