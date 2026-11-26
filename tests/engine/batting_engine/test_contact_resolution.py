import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.engine.batting_engine.contact import (
    ContactResolver,
    resolve_contact_outcome,
    fielder_for_landing,
    PARK_FENCE_CENTER_FT,
    PARK_FENCE_LINE_FT,
    FOUL_LINE_DEG,
    FIELDERS,
)

def test_contact_subpackage_exports():
    assert ContactResolver is not None
    assert callable(resolve_contact_outcome)
    assert callable(fielder_for_landing)
    assert PARK_FENCE_CENTER_FT == 420.0
    assert PARK_FENCE_LINE_FT == 350.0
    assert FOUL_LINE_DEG == 45.0
    assert isinstance(FIELDERS, tuple)


def test_contact_outcome_functional_classification():
    # 108 mph at 28 deg straight away = Home Run clearing 420 ft CF wall
    hr = resolve_contact_outcome(108.0, 28.0, 0.0)
    assert hr['call'] == 'HOME_RUN'
    assert hr['is_in_play'] is True
    assert hr['batted_ball'] is not None

    # Routine popup to catcher/infield
    grounder = resolve_contact_outcome(80.0, -10.0, 0.0)
    assert grounder['call'] == 'IN_PLAY_OUT'
    assert grounder['fielder_name'] == 'P'

