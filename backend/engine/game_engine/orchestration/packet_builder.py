"""
Packet & Telemetry Builders.

Pure builder functions that construct standardized Gameday2DPitchPacket telemetry
and UI pitch detail dictionaries from a PitchContext.
"""

import os
import random
from typing import Any, Dict, Optional

from .pitch_context import PitchContext
from ...pitching_engine.pitch_execution.pitch_shape import (
    build_pitch_shape,
    shape_telemetry,
)

def is_swing_decision_telemetry_enabled() -> bool:
    try:
        import backend.engine.game_engine.engine as engine_module
        if hasattr(engine_module, 'SWING_DECISION_TELEMETRY'):
            return bool(engine_module.SWING_DECISION_TELEMETRY)
    except (ImportError, AttributeError):
        pass
    return os.environ.get("SWING_DECISION_TELEMETRY", "0").strip().lower() in ("1", "true", "on", "yes")


def build_gameday_packet(
    context: PitchContext,
    result: Dict[str, Any],
    rng: Optional[random.Random] = None,
) -> Dict[str, Any]:
    """
    Constructs a standardized Gameday2DPitchPacket telemetry dictionary
    from a populated PitchContext and result payload.
    """
    if rng is None:
        rng = random.Random()

    pitcher = context.pitcher.pitcher
    batter = context.batter.batter
    delivery = context.delivery or {}
    strat_result = delivery.get("strat_result", {})

    pitcher_name = getattr(pitcher, "name", "Pitcher") if pitcher else "Pitcher"
    batter_name = getattr(batter, "name", "Batter") if batter else "Batter"
    batter_id = getattr(batter, "id", 1) if batter else 1
    pitcher_hand = context.pitcher.pitcher_hand

    base_release = getattr(pitcher, "release_point_ft", None) or {
        "x": -1.85 if pitcher_hand == "R" else 1.85,
        "y": 54.6,
        "z": 5.9,
    }
    consistency = float(
        getattr(pitcher, "consistency", getattr(pitcher, "release_consistency", 80.0)) or 80.0
    )
    jitter_sigma = max(0.0, (100.0 - consistency) / 100.0 * 0.04)
    jitter_x = round(rng.gauss(0, jitter_sigma), 3) if jitter_sigma > 0 else 0.0
    jitter_y = round(rng.gauss(0, jitter_sigma * 0.5), 3) if jitter_sigma > 0 else 0.0
    jitter_z = round(rng.gauss(0, jitter_sigma), 3) if jitter_sigma > 0 else 0.0

    release = {
        "x": round(float(base_release.get("x", -1.85 if pitcher_hand == "R" else 1.85)) + jitter_x, 3),
        "y": round(float(base_release.get("y", 54.6)) + jitter_y, 3),
        "z": round(float(base_release.get("z", 5.9)) + jitter_z, 3),
    }

    # Tunneling synergy detection (O(1))
    cur_pitch_name = delivery.get("selected_pitch")
    cur_pitch_obj = None
    if hasattr(pitcher, "get_pitch_fast"):
        cur_pitch_obj = pitcher.get_pitch_fast(cur_pitch_name)
    tunnel_partners = list(cur_pitch_obj.get("tunnel_partners", []) if cur_pitch_obj else [])

    seq = context.pitcher.pitch_sequence
    # If seq includes current pitch at the end, prev pitch is at [-2]; otherwise [-1]
    prev_pitch_name = None
    if len(seq) >= 2 and seq[-1] == cur_pitch_name:
        prev_pitch_name = seq[-2]
    elif len(seq) >= 1 and seq[-1] != cur_pitch_name:
        prev_pitch_name = seq[-1]

    prev_pitch_obj = (
        pitcher.get_pitch_fast(prev_pitch_name)
        if hasattr(pitcher, "get_pitch_fast") and prev_pitch_name
        else None
    )
    prev_pitch_id = prev_pitch_obj.get("id") if prev_pitch_obj else prev_pitch_name

    is_tunneled = bool(
        prev_pitch_id and (
            prev_pitch_id in tunnel_partners
            or (prev_pitch_name and prev_pitch_name in tunnel_partners)
        )
    )

    shape = build_pitch_shape(delivery)
    command_rating = float(
        getattr(context.pitcher.ratings, "effective_command", 75.0)
        if hasattr(context.pitcher.ratings, "effective_command")
        else delivery.get("adjusted_ratings", {}).get("base_command", 70.0)
    )

    cur_pitch_count = context.pitcher.pitch_count
    runners = context.count.runners

    return {
        "meta": {
            "pitchNumber": cur_pitch_count,
            "pitcherName": pitcher_name,
            "pitcherHand": pitcher_hand,
            "pitcherOvr": 85,
            "commandRating": int(command_rating),
            "staminaPct": max(10, 100 - cur_pitch_count),
            "pitchesThrown": cur_pitch_count,
            "armSlot": getattr(pitcher, "arm_slot", "THREE_QUARTERS"),
            "armSlotAngleDeg": getattr(pitcher, "arm_slot_angle_deg", 50.0),
            "consistency": consistency,
            "releaseConsistency": consistency,
            "motionBio": getattr(pitcher, "motion_bio", None),
            "inning": context.count.inning,
            "isTopInning": True,
            "count": {
                "balls": context.count.balls,
                "strikes": context.count.strikes,
                "outs": context.count.outs,
            },
            "runnersOnBase": {
                "first": bool(runners[0] if len(runners) > 0 else False),
                "second": bool(runners[1] if len(runners) > 1 else False),
                "third": bool(runners[2] if len(runners) > 2 else False),
            },
            "batterName": batter_name,
            "batterId": batter_id,
            "situationCategory": context.count.situation,
        },
        "release": release,
        "tunneling": {
            "isTunneled": is_tunneled,
            "previousPitchId": prev_pitch_id,
            "tunnelPartners": tunnel_partners,
        },
        "strategy": {
            "repertoireProbabilities": strat_result.get("repertoire_probabilities", {}),
            "selectedPitch": delivery.get("selected_pitch", "4-Seam Fastball"),
            "dynamicModifier": strat_result.get("dynamic_modifier", 1.0),
            "strategyName": strat_result.get("strategy_name", "UNKNOWN"),
            "rationale": strat_result.get("rationale", ""),
        },
        "intent": {
            "targetX": delivery.get("target_x", 0.0),
            "targetZ": delivery.get("target_z", 2.5),
            "intendedZone": delivery.get("intended_zone_cat", "heart"),
            "targetSpeedMph": delivery.get("velocity_mph", 94.0),
            "isManualOverride": delivery.get("is_manual_override", False),
        },
        "execution": {
            "realizedX": delivery.get("realized_x", 0.0),
            "realizedZ": delivery.get("realized_z", 2.5),
            "realizedSpeedMph": delivery.get("velocity_mph", 94.0),
            "releaseSpeedMph": delivery.get("release_speed_mph", delivery.get("velocity_mph", 94.0)),
            "horizontalBreakInches": delivery.get("horizontal_break_in", 0.0),
            "inducedVerticalBreakInches": delivery.get("induced_vertical_break_in", 0.0),
            "maxRadiusInches": delivery.get("max_radius_inches", 0.0),
            "radialMissInches": delivery.get("radial_miss_in", 0.0),
            "deltaXInches": delivery.get("delta_x_in", 0.0),
            "deltaZInches": delivery.get("delta_z_in", 0.0),
            "sigmaXFeet": round(float(delivery.get("sigma", 0.05)), 3),
            "sigmaZFeet": round(float(delivery.get("sigma", 0.05)), 3),
            "isHeartZoneLeak": delivery.get("is_heart_leak", False),
            "hitShadowZoneTarget": delivery.get("hit_shadow_target", False),
            "realizedZoneCategory": delivery.get("realized_zone_cat", "shadow"),
            "pitchId": cur_pitch_obj.get("id", "") if cur_pitch_obj else "",
            "spinRateRpm": cur_pitch_obj.get("spin_rate_rpm", delivery.get("spin_rpm", 2400)) if cur_pitch_obj else delivery.get("spin_rpm", 2400),
            "spinAxisDeg": cur_pitch_obj.get("spin_axis_deg", 180.0) if cur_pitch_obj else 180.0,
            "abilityTier": delivery.get("ability_tier"),
            "timingTier": delivery.get("timing_tier"),
            "timingLabel": delivery.get("timing_label"),
            "baseRadiusInches": delivery.get("base_radius_inches"),
            "executedRadiusInches": delivery.get("executed_radius_inches"),
            "shape": shape_telemetry(shape),
        },
        "result": result,
    }


def build_pitch_details(
    context: PitchContext,
    description: str,
    result_type: Optional[str] = None,
    batter_decision: Optional[str] = None,
    exit_velo: Optional[float] = None,
    launch_angle: Optional[float] = None,
    spray_angle: Optional[float] = None,
    batted_ball: Optional[Dict[str, Any]] = None,
    swing_decision: Optional[Dict[str, Any]] = None,
    gameday_packet: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Constructs a detailed UI pitch summary dictionary from a PitchContext.
    """
    delivery = context.delivery or {}
    strat_result = delivery.get("strat_result", {})
    radial_miss_in = float(delivery.get("radial_miss_in", 0.0))

    target_zone = context.inputs.target_zone if context.inputs else None

    details = {
        "pitch_name": delivery.get("selected_pitch", "4-Seam Fastball"),
        "velocity_mph": delivery.get("velocity_mph", 94.0),
        "spin_rpm": delivery.get("spin_rpm", 2400),
        "intended_zone": delivery.get("nominal_zone", target_zone or "heart"),
        "actual_zone": context.actual_zone_name or "ZONE_5",
        "batter_decision": batter_decision,
        "pitch_result": result_type,
        "exit_velocity_mph": exit_velo,
        "launch_angle_deg": launch_angle,
        "spray_angle_deg": spray_angle,
        "batted_ball": batted_ball,
        "description": description,
        "strategy_name": strat_result.get("strategy_name", "UNKNOWN"),
        "command_quality": (
            "PINPOINT"
            if radial_miss_in <= 2.0
            else "TARGET_EXECUTED"
            if radial_miss_in <= 4.0
            else "SLIGHT_MISS"
        ),
        "pitch_effectiveness": delivery.get("pitch_effectiveness", 75.0),
        "adjusted_ratings": delivery.get("adjusted_ratings", {}),
        "gameday_packet": gameday_packet or context.gameday_packet or {},
    }

    if is_swing_decision_telemetry_enabled() and swing_decision is not None:
        details["swing_decision"] = swing_decision

    return details
