import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.engine.batting_engine.swing_decision import (
    BatterStrategy,
    SwingEvaluation,
    MODEL_CONFIG,
)

def test_swing_decision_subpackage_exports():
    assert BatterStrategy is not None
    assert SwingEvaluation is not None
    assert isinstance(MODEL_CONFIG, dict)
    assert 'count_logit' in MODEL_CONFIG or 'approach' in MODEL_CONFIG


def test_batter_strategy_hydrates_dict_ratings():
    strategy = BatterStrategy({'vision': 65.0, 'power': 70.0})
    assert strategy.ratings.vision == 65.0
    assert strategy.ratings.power == 70.0

