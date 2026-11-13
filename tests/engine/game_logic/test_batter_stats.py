import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from backend.engine.game_engine.game_logic.batter_stats import BatterStatsTracker


def _batter(id_, name):
    b = MagicMock()
    b.id = id_
    b.name = name
    return b


def test_get_line_creates_default():
    t = BatterStatsTracker()
    line = t.get_line(_batter(1, 'Doe'))
    assert line == {'at_bats': 0, 'hits': 0, 'rbis': 0, 'home_runs': 0}


def test_get_line_mutates_persist():
    t = BatterStatsTracker()
    b = _batter(1, 'Doe')
    t.get_line(b)['hits'] += 1
    assert t.get_line(b)['hits'] == 1


def test_stats_key_format():
    t = BatterStatsTracker()
    assert t.stats_key(_batter(42, 'Smith')) == '42:Smith'
    assert t.stats_key({'id': 42, 'name': 'Smith'}) == '42:Smith'


def test_copy_is_deep():
    t = BatterStatsTracker()
    b = _batter(1, 'Doe')
    t.get_line(b)['hits'] = 2
    snap = t.copy()
    snap['1:Doe']['hits'] = 99
    assert t.get_line(b)['hits'] == 2
