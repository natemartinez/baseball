import random
import pytest
from backend.models.player import Player
from backend.engine.game_engine.orchestration.pitch_orchestrator import (
    PitchFlowOrchestrator,
    PitchPhase,
)

def test_orchestrator_runs_complete_context_lifecycle():
    rng = random.Random(42)
    orchestrator = PitchFlowOrchestrator(rng=rng)

    pitcher = Player(id=1, name="Pitcher", ratings={"control": 80, "stamina": 80, "velocity": 94, "break": 80})
    batter = Player(id=2, name="Batter", ratings={"contact": 80, "power": 80, "discipline": 75})

    started = orchestrator.start_pitch(
        pitcher=pitcher,
        batter=batter,
        balls=0,
        strikes=0,
        outs=0,
        runners=(False, False, False),
        situation="EMPTY_NEUTRAL",
        pitch_count=1,
        pitch_name="4-Seam Fastball",
    )

    assert orchestrator.phase == PitchPhase.THROWN
    assert orchestrator.context is not None
    assert orchestrator.context.delivery["selected_pitch"] == "4-Seam Fastball"
    assert orchestrator.context.gameday_packet is not None
    assert orchestrator.context.pitch_details is not None

    resolved = orchestrator.resolve_pitch(batter_approach="CONTACT")

    assert orchestrator.phase == PitchPhase.OUTCOME_RESOLVED
    assert orchestrator.context.activity is not None
    assert orchestrator.context.reaction is not None
    assert resolved["activity"] == orchestrator.context.activity

    orchestrator.mark_applied()
    assert orchestrator.phase == PitchPhase.STATE_APPLIED
    orchestrator.finish()
    assert orchestrator.phase == PitchPhase.IDLE

def test_orchestrator_accepts_precomputed_delivery_without_pitching_engine():
    orchestrator = PitchFlowOrchestrator(rng=random.Random(1))
    pitcher = Player(id=1, name="Pitcher", ratings={"control": 75, "stamina": 75})
    batter = Player(id=2, name="Batter", ratings={"contact": 75, "power": 75})

    canned_delivery = {
        "selected_pitch": "Changeup",
        "velocity_mph": 85.0,
        "spin_rpm": 1900,
        "realized_x": 0.0,
        "realized_z": 2.5,
        "target_x": 0.0,
        "target_z": 2.5,
        "radial_miss_in": 0.0,
        "delta_x_in": 0.0,
        "delta_z_in": 0.0,
        "sigma": 0.01,
        "is_heart_leak": False,
        "hit_shadow_target": False,
        "intended_zone_cat": "heart",
        "realized_zone_cat": "heart",
        "is_strike": True,
        "is_manual_override": False,
        "adjusted_ratings": {"base_command": 75.0},
        "strat_result": {
            "repertoire_probabilities": {"Changeup": 1.0},
            "dynamic_modifier": 1.0,
            "strategy_name": "PRACTICE_DRILL",
            "rationale": "Direct injection",
        },
    }

    started = orchestrator.start_pitch(
        pitcher=pitcher,
        batter=batter,
        balls=0,
        strikes=0,
        outs=0,
        runners=(False, False, False),
        situation="EMPTY_NEUTRAL",
        pitch_count=1,
        delivery=canned_delivery,
    )

    assert orchestrator.context.delivery["selected_pitch"] == "Changeup"
    assert orchestrator.context.delivery["velocity_mph"] == 85.0

