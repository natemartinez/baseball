import pytest
from backend.models.player import Player
from backend.engine.game_engine.orchestration.pitch_context import (
    PitchContext,
    CountSnapshot,
    PitchInput,
)

def test_pitch_context_snapshots_participant_ratings_and_match_state():
    pitcher = Player(
        id=101,
        name="Gerrit Cole",
        position="SP",
        ratings={"control": 84, "velocity": 97, "break": 88, "stamina": 85},
    )
    batter = Player(
        id=202,
        name="Aaron Judge",
        position="RF",
        ratings={"contact": 80, "power": 99, "discipline": 85},
    )
    count = CountSnapshot(
        balls=1,
        strikes=2,
        outs=1,
        runners=(True, False, False),
        inning=3,
        score_diff=0,
        situation="BEHIND_IN_COUNT",
    )
    inputs = PitchInput(
        pitch_intent="CHASE",
        pitch_name="Slider",
        target_zone="shadow",
    )

    ctx = PitchContext.create(
        pitch_id="pitch-test-001",
        pitcher=pitcher,
        batter=batter,
        count=count,
        pitch_input=inputs,
        pitch_count=42,
        recent_pitches=["4-Seam Fastball"],
    )

    assert ctx.pitch_id == "pitch-test-001"
    assert ctx.count.balls == 1
    assert ctx.count.strikes == 2
    assert ctx.count.runners == (True, False, False)
    # Ratings must be pre-calculated in the participant snapshot
    assert ctx.pitcher.pitch_count == 42
    assert ctx.pitcher.ratings.base_command == 84.0
    assert ctx.pitcher.ratings.fatigue_pct >= 0.0
    assert ctx.batter.ratings is not None

def test_pitch_context_serializes_to_black_box_dict():
    pitcher = Player(id=1, name="Pitcher", ratings={"control": 75, "stamina": 75})
    batter = Player(id=2, name="Batter", ratings={"contact": 75, "power": 75})
    count = CountSnapshot(balls=0, strikes=0, outs=0, runners=(False, False, False), inning=1, score_diff=0, situation="EMPTY_NEUTRAL")
    inputs = PitchInput()

    ctx = PitchContext.create(
        pitch_id="pitch-test-002",
        pitcher=pitcher,
        batter=batter,
        count=count,
        pitch_input=inputs,
        pitch_count=10,
    )
    dump = ctx.to_dict()

    assert dump["pitch_id"] == "pitch-test-002"
    assert dump["count"]["balls"] == 0
    assert dump["pitcher"]["name"] == "Pitcher"
    assert dump["pitcher"]["pitch_count"] == 10
    assert "effective_command" in dump["pitcher"]["ratings"]

