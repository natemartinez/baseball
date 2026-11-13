import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from backend.engine.game_engine.game_logic.base_running import advance_on_hit, advance_on_walk

BATTER = {'id': 1, 'name': 'Doe', 'jersey_number': 7, 'position': 'RF', 'team': 'Away'}
RUNNER_A = {'id': 2, 'name': 'Smith'}
RUNNER_B = {'id': 3, 'name': 'Jones'}
RUNNER_C = {'id': 4, 'name': 'Clark'}
EMPTY = {'first': None, 'second': None, 'third': None}


def test_single_empty_bases():
    new_bases, runs = advance_on_hit(EMPTY, 1, BATTER)
    assert runs == 0
    assert new_bases['first'] == BATTER
    assert new_bases['second'] is None


def test_home_run_clears_bases():
    bases = {'first': RUNNER_A, 'second': RUNNER_B, 'third': RUNNER_C}
    new_bases, runs = advance_on_hit(bases, 4, BATTER)
    assert runs == 4
    assert all(v is None for v in new_bases.values())


def test_double_scores_runner_on_second():
    bases = {'first': None, 'second': RUNNER_A, 'third': None}
    new_bases, runs = advance_on_hit(bases, 2, BATTER)
    assert runs == 1
    assert new_bases['second'] == BATTER


def test_does_not_mutate_input():
    bases = {'first': RUNNER_A, 'second': None, 'third': None}
    original = dict(bases)
    advance_on_hit(bases, 1, BATTER)
    assert bases == original


def test_walk_no_runners():
    new_bases, runs = advance_on_walk(EMPTY, BATTER)
    assert runs == 0
    assert new_bases['first'] == BATTER


def test_walk_bases_loaded_scores_run():
    bases = {'first': RUNNER_A, 'second': RUNNER_B, 'third': RUNNER_C}
    new_bases, runs = advance_on_walk(bases, BATTER)
    assert runs == 1
    assert new_bases['first'] == BATTER
    assert new_bases['second'] == RUNNER_A
    assert new_bases['third'] == RUNNER_B

