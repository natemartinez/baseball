import random
import pytest
from backend.models.player import Player
from backend.engine.game_engine.orchestration.pitch_context import (
    PitchContext,
    CountSnapshot,
    PitchInput,
)
from backend.engine.game_engine.orchestration.packet_builder import (
    build_gameday_packet,
    build_pitch_details,
)

def test_build_gameday_packet_from_context():
    pitcher = Player(id=1, name="Gerrit Cole", position="P", handedness="R", ratings={"control": 85, "stamina": 85})
    batter = Player(id=2, name="Rafael Devers", position="3B", handedness="L", ratings={"contact": 85, "power": 85})
    count = CountSnapshot(balls=0, strikes=1, outs=0, runners=(False, False, False), inning=1, score_diff=0, situation="AHEAD_IN_COUNT")
    inputs = PitchInput(pitch_name="4-Seam Fastball")

    ctx = PitchContext.create(
        pitch_id="p-1",
        pitcher=pitcher,
        batter=batter,
        count=count,
        pitch_input=inputs,
        pitch_count=15,
        recent_pitches=["Slider", "4-Seam Fastball"],
    )
    ctx.delivery = {
        "selected_pitch": "4-Seam Fastball",
        "velocity_mph": 97.5,
        "spin_rpm": 2450,
        "realized_x": 0.2,
        "realized_z": 2.4,
        "target_x": 0.0,
        "target_z": 2.5,
        "radial_miss_in": 2.5,
        "delta_x_in": 2.4,
        "delta_z_in": -1.2,
        "sigma": 0.05,
        "is_heart_leak": False,
        "hit_shadow_target": True,
        "intended_zone_cat": "shadow",
        "realized_zone_cat": "shadow",
        "is_strike": True,
        "is_manual_override": False,
        "strat_result": {
            "repertoire_probabilities": {"4-Seam Fastball": 0.7, "Slider": 0.3},
            "dynamic_modifier": 1.0,
            "strategy_name": "CHALLENGE_STRIKE",
            "rationale": "Ahead in count",
        },
    }
    ctx.actual_zone_name = "ZONE_5"
    ctx.is_strike = True

    packet = build_gameday_packet(ctx, result={"call": None, "isStrike": True, "description": "In flight"}, rng=random.Random(42))

    assert packet["meta"]["pitcherName"] == "Gerrit Cole"
    assert packet["meta"]["pitcherHand"] == "R"
    assert packet["intent"]["targetSpeedMph"] == 97.5
    assert packet["execution"]["realizedSpeedMph"] == 97.5
    assert "tunneling" in packet
    assert "shape" in packet["execution"]

def test_build_pitch_details_from_context():
    pitcher = Player(id=1, name="Gerrit Cole", position="P", ratings={"control": 85, "stamina": 85})
    batter = Player(id=2, name="Rafael Devers", position="3B", ratings={"contact": 85, "power": 85})
    count = CountSnapshot(balls=0, strikes=0, outs=0, runners=(False, False, False), inning=1, score_diff=0, situation="EMPTY_NEUTRAL")
    ctx = PitchContext.create("p-2", pitcher, batter, count, PitchInput(), pitch_count=1)
    ctx.delivery = {
        "selected_pitch": "Changeup",
        "velocity_mph": 88.0,
        "spin_rpm": 1800,
        "radial_miss_in": 1.2,
        "strat_result": {"strategy_name": "NEUTRAL_FIRST_PITCH"},
    }
    ctx.actual_zone_name = "ZONE_14"

    details = build_pitch_details(ctx, description="Pitch in flight")

    assert details["pitch_name"] == "Changeup"
    assert details["velocity_mph"] == 88.0
    assert details["command_quality"] == "PINPOINT"  # <= 2.0 inches
    assert details["description"] == "Pitch in flight"

