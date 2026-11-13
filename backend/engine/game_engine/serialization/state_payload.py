"""
Game State Payload Serialization.

Serializes the authoritative engine game state into the standard frontend JSON payload.
"""

from typing import Any, Dict

from backend.engine.batting_engine import (
    BatterInstanceManager,
    normalize_traits,
)
from .arsenal_payload import build_arsenal_payload


def build_state_payload(engine: Any) -> Dict[str, Any]:
    """
    Constructs the authoritative client payload representing the current game state,
    including lineups, score, base runners, count, and pitcher/batter snapshots.
    """
    cur_p = engine.current_pitcher_obj() if hasattr(engine, 'current_pitcher_obj') else None
    cur_b = engine.current_batter_obj() if hasattr(engine, 'current_batter_obj') else None

    p_name = getattr(cur_p, 'name', 'Pitcher') if cur_p else 'Pitcher'
    p_num = getattr(cur_p, 'number', 26) if cur_p else 26
    p_pos = getattr(cur_p, 'position', 'SP') if cur_p else 'SP'
    p_team = engine.home_name if engine.top_bottom == 'TOP' else engine.away_name

    b_name = getattr(cur_b, 'name', 'Batter') if cur_b else 'Batter'
    b_num = getattr(cur_b, 'number', 99) if cur_b else 99
    b_pos = getattr(cur_b, 'position', 'RF') if cur_b else 'RF'
    b_team = engine.away_name if engine.top_bottom == 'TOP' else engine.home_name

    pitch_count = (
        engine.pitch_count_home if engine.top_bottom == 'TOP' else engine.pitch_count_away
    )
    pitcher_hand = (
        (
            'L'
            if str(getattr(cur_p, 'handedness', 'R') or 'R').upper().startswith('L')
            else 'R'
        )
        if cur_p
        else 'R'
    )
    batter_ratings = BatterInstanceManager.get_adjusted_ratings(
        cur_b,
        balls=engine.balls,
        strikes=engine.strikes,
        pitcher_hand=pitcher_hand,
    )

    if hasattr(engine, '_stats_tracker') and engine._stats_tracker is not None:
        batter_line = dict(engine._stats_tracker.get_line(cur_b))
    elif hasattr(engine, '_batter_game_stats'):
        stats_key = (
            engine._batter_stats_key(cur_b)
            if hasattr(engine, '_batter_stats_key')
            else f"{getattr(cur_b, 'id', 0)}:{getattr(cur_b, 'name', '')}"
        )
        batter_line = dict(
            engine._batter_game_stats.get(
                stats_key,
                {'at_bats': 0, 'hits': 0, 'rbis': 0, 'home_runs': 0},
            )
        )
    else:
        batter_line = {'at_bats': 0, 'hits': 0, 'rbis': 0, 'home_runs': 0}

    cur_pitcher_state = (
        engine.current_pitcher_state()
        if hasattr(engine, 'current_pitcher_state')
        else None
    )

    break_rating = (
        cur_p.get_rating('break_rating', 99)
        if hasattr(cur_p, 'get_rating')
        else getattr(cur_p, 'break_rating', 99)
    )
    velocity_rating = (
        cur_p.get_rating('velocity_rating', 98)
        if hasattr(cur_p, 'get_rating')
        else getattr(cur_p, 'velocity_rating', 98)
    )
    arm_strength = (
        cur_p.get_rating('arm_strength', 97)
        if hasattr(cur_p, 'get_rating')
        else getattr(cur_p, 'arm_strength', 97)
    )
    control = (
        cur_p.get_rating('control', 68)
        if hasattr(cur_p, 'get_rating')
        else getattr(cur_p, 'control', 68)
    )

    payload = {
        'inning': engine.inning,
        'top_bottom': engine.top_bottom,
        'outs': engine.outs,
        'balls': engine.balls,
        'strikes': engine.strikes,
        'score': {
            'home': engine.score.get(engine.home_name, 0),
            'away': engine.score.get(engine.away_name, 0),
        },
        'bases': engine.bases,
        'current_batter': {
            'id': getattr(cur_b, 'id', 201) if cur_b else 201,
            'name': b_name,
            'jersey_number': int(b_num) if str(b_num).isdigit() else 99,
            'position': b_pos,
            'team': b_team,
            'handedness': getattr(cur_b, 'handedness', 'R') if cur_b else 'R',
            'power': int(round(batter_ratings.power)),
            'contact': int(round(batter_ratings.contact)),
            'vision': int(round(batter_ratings.vision)),
            'traits': normalize_traits(cur_b),
            'hot_zones': {k: round(v, 3) for k, v in batter_ratings.hot_zones.items()},
            'stats': batter_line,
        },
        'current_pitcher': {
            'id': getattr(cur_p, 'id', 101) if cur_p else 101,
            'name': p_name,
            'jersey_number': int(p_num) if str(p_num).isdigit() else 26,
            'position': p_pos,
            'team': p_team,
            'throws': pitcher_hand,
            'stamina': float(getattr(cur_p, 'stamina', 75.0) if cur_p else 75.0),
            'composure': float(getattr(cur_p, 'composure', 75.0) if cur_p else 75.0),
            'consistency': float(
                getattr(cur_p, 'consistency', getattr(cur_p, 'release_consistency', 80.0))
                if cur_p
                else 80.0
            ),
            'release_consistency': float(
                getattr(cur_p, 'consistency', getattr(cur_p, 'release_consistency', 80.0))
                if cur_p
                else 80.0
            ),
            'motion_bio': getattr(cur_p, 'motion_bio', None),
            'arm_slot': getattr(cur_p, 'arm_slot', 'THREE_QUARTERS') if cur_p else 'THREE_QUARTERS',
            'arm_slot_angle_deg': float(getattr(cur_p, 'arm_slot_angle_deg', 50.0) if cur_p else 50.0),
            'release_point_ft': dict(
                getattr(
                    cur_p,
                    'release_point_ft',
                    {
                        'x': -1.85 if pitcher_hand == 'R' else 1.85,
                        'y': 54.6,
                        'z': 5.9,
                    },
                )
            )
            if cur_p
            else {
                'x': -1.85 if pitcher_hand == 'R' else 1.85,
                'y': 54.6,
                'z': 5.9,
            },
            'break_rating': int(break_rating),
            'velocity_rating': int(velocity_rating),
            'arm_strength': int(arm_strength),
            'control': int(control),
            'arsenal': build_arsenal_payload(cur_p, active_state=cur_pitcher_state),
            'stats': {
                'pitches_thrown': pitch_count,
                'strikeouts': 6,
                'walks': 1,
                'hits_allowed': 3,
                'runs_allowed': 1,
            },
        },
        'game_over': engine.game_over,
        'home_team': engine.home_name,
        'away_team': engine.away_name,
        'win_probability': 0.52,
    }

    if hasattr(engine, 'calculate_strategy_and_intent'):
        payload['strategy_intent'] = engine.calculate_strategy_and_intent(payload)

    return payload

