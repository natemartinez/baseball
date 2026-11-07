"""
Strategy recommendation payload for the scoreboard/strategy UI.

This is the pure-function home of the former
``GameEngine.calculate_strategy_and_intent``. It ranks the pitcher's arsenal and
the 13 target zones for the current game state and returns the exact dict shape
consumed by ``get_game_state_payload`` and the Expo client.
"""

from typing import Any, Dict

from .intent import pitch_specific_zone


def calculate_strategy_and_intent(
    outs: int,
    balls: int,
    strikes: int,
    bases: Dict[str, Any],
    batter: Dict[str, Any],
    pitcher: Dict[str, Any],
) -> Dict[str, Any]:
    is_bases_loaded = bases.get('first') is not None and bases.get('second') is not None and bases.get('third') is not None
    is_double_play = bases.get('first') is not None and outs < 2
    is_scoring_pos = (bases.get('second') is not None or bases.get('third') is not None) and outs < 2

    is_ahead = strikes == 2
    is_behind = (balls == 3 and strikes < 2) or (balls == 2 and strikes == 0)
    is_full_count = balls == 3 and strikes == 2

    if is_bases_loaded:
        situation_tag = 'BASES_LOADED'
    elif is_double_play:
        situation_tag = 'DOUBLE_PLAY_SITUATION'
    elif is_scoring_pos:
        situation_tag = 'SCORING_POSITION'
    else:
        situation_tag = 'BASES_EMPTY'

    if is_ahead:
        count_context = f'AHEAD ({balls}-{strikes}) - PUT AWAY MODE'
    elif is_behind:
        count_context = f'BEHIND ({balls}-{strikes}) - STRIKE DEMAND'
    elif is_full_count:
        count_context = 'FULL COUNT (3-2) - HIGH LEVERAGE BATTLE'
    elif balls == 0 and strikes == 0:
        count_context = 'FIRST PITCH (0-0) - ESTABLISH COUNT'
    else:
        count_context = f'NEUTRAL ({balls}-{strikes}) - SETUP & ATTACK'

    if is_bases_loaded and is_ahead:
        strategy_name = 'BASES_LOADED_PUNCHOUT'
        rationale = 'Bases loaded with 2 strikes. Zero margin for error. Attack edges with high-whiff putaway arsenal to secure the strikeout.'
    elif is_bases_loaded and is_behind:
        strategy_name = 'BASES_LOADED_COMMAND_STRIKE'
        rationale = 'Bases loaded behind in count. Ball 4 forces home a run! Must challenge the zone with high-velocity 4-Seamer or Sinker.'
    elif is_bases_loaded:
        strategy_name = 'BASES_LOADED_LEVERAGE'
        rationale = 'Bases loaded pressure. Induce weak ground-ball or foul contact to prevent extra-base damage.'
    elif is_double_play:
        strategy_name = 'DOUBLE_PLAY_GROUNDER_HUNT'
        rationale = f'Runner on 1st with {outs} out. Target bottom of zone with Power Sinker (64% GB rate) to roll inning-ending double play.'
    elif is_ahead:
        strategy_name = 'TWO_STRIKE_PUT_AWAY'
        rationale = f'Ahead in count ({balls}-{strikes}). Expand zone into chase corridors with high-spin sweeper or breaking ball.'
    elif is_behind:
        strategy_name = 'CRITICAL_ZONE_CHALLENGE'
        rationale = f'Behind in count ({balls}-{strikes}). Paint strike zone shadow with high-velo fastball to prevent free pass.'
    elif is_scoring_pos:
        strategy_name = 'SCORING_POSITION_SUPPRESSION'
        rationale = f'Runner in scoring position with {outs} out. Suppress elevated contact to avoid sacrifice fly; attack batter cold zones.'
    else:
        strategy_name = 'NEUTRAL_PITCH_MIX'
        rationale = f'Bases empty, count {balls}-{strikes}. Balance fastball velocity and sweeper spin while avoiding batter hot zones.'

    arsenal = pitcher.get('arsenal', [])
    if not arsenal:
        arsenal = [
            {'name': '4-Seam Fastball', 'velocity_mph': 97.4, 'spin_rpm': 2480, 'break_rating': 90, 'control_rating': 84, 'statcast': {'whiff_pct': 25.0, 'chase_pct': 24.2, 'gb_pct': 34.0, 'stuff_plus': 118, 'zone_pct': 56.0, 'run_value': -4}},
            {'name': 'Spin Monster Sweeper', 'velocity_mph': 83.5, 'spin_rpm': 2980, 'break_rating': 99, 'control_rating': 80, 'statcast': {'whiff_pct': 44.5, 'chase_pct': 36.5, 'gb_pct': 42.0, 'stuff_plus': 135, 'zone_pct': 42.0, 'run_value': -12}},
            {'name': 'Power Sinker', 'velocity_mph': 95.8, 'spin_rpm': 2310, 'break_rating': 88, 'control_rating': 85, 'statcast': {'whiff_pct': 14.0, 'chase_pct': 28.0, 'gb_pct': 57.0, 'stuff_plus': 112, 'zone_pct': 58.0, 'run_value': -7}},
            {'name': 'Spike Curveball', 'velocity_mph': 81.2, 'spin_rpm': 2840, 'break_rating': 94, 'control_rating': 78, 'statcast': {'whiff_pct': 38.0, 'chase_pct': 33.0, 'gb_pct': 48.0, 'stuff_plus': 122, 'zone_pct': 46.0, 'run_value': -6}},
        ]

    pitch_weights_raw = []
    for item in arsenal:
        w = 100.0
        stat = item.get('statcast', {})
        name = item.get('name', '')
        if is_double_play:
            if 'Sinker' in name:
                w *= 2.8
            elif 'Curveball' in name or 'Changeup' in name:
                w *= 1.3
            elif 'Fastball' in name:
                w *= 0.45
        if is_bases_loaded:
            if is_behind:
                if 'Fastball' in name or 'Sinker' in name:
                    w *= 2.2
                else:
                    w *= 0.4
            elif is_ahead:
                if 'Sweeper' in name:
                    w *= 2.5
        if is_ahead:
            if 'Sweeper' in name:
                w *= 3.0
            elif 'Curveball' in name:
                w *= 2.0
            elif 'Fastball' in name:
                w *= 0.55
        elif is_behind:
            if 'Fastball' in name:
                w *= 2.6
            elif 'Sinker' in name:
                w *= 1.9
            elif 'Sweeper' in name:
                w *= 0.35

        if stat:
            if stat.get('stuff_plus', 0) > 125:
                w *= 1.15
            if stat.get('whiff_pct', 0) > 40.0 and is_ahead:
                w *= 1.25
            if stat.get('gb_pct', 0) > 60.0 and is_double_play:
                w *= 1.35
        pitch_weights_raw.append({'item': item, 'w': w})

    total_pitch_weight = max(sum(x['w'] for x in pitch_weights_raw), 0.001)
    sorted_pitches = sorted(pitch_weights_raw, key=lambda x: x['w'], reverse=True)
    ranked_pitch_weights = []
    for idx, pw_dict in enumerate(sorted_pitches):
        item = pw_dict['item']
        w = pw_dict['w']
        prob = (w / total_pitch_weight) * 100.0
        if idx == 0 and is_double_play:
            reason = 'Primary weapon: Elite 64.0% GB rate to roll double play'
        elif idx == 0 and is_ahead:
            reason = 'Putaway weapon: 44.5% Whiff & elite spin rate'
        elif idx == 0 and is_behind:
            reason = 'Strike demand: High velocity & zone command'
        elif idx == len(sorted_pitches) - 1:
            reason = 'Deprioritized in current game leverage'
        else:
            reason = 'Secondary tactical option'

        ranked_pitch_weights.append({
            'pitch_name': item['name'],
            'weight': round(w, 1),
            'probability_pct': round(prob, 1),
            'rank': idx + 1,
            'is_most_likely': (idx == 0),
            'is_least_likely': (idx == len(sorted_pitches) - 1),
            'reasoning': reason,
            'statcast': item.get('statcast', {})
        })

    ALL_ZONES = [
        'upper-in', 'upper-middle', 'upper-away',
        'middle-in', 'heart', 'middle-away',
        'lower-in', 'lower-middle', 'lower-away',
        'chase-high', 'chase-low', 'chase-in', 'chase-away'
    ]
    RULEBOOK_STRIKES = {
        'upper-in', 'upper-middle', 'upper-away',
        'middle-in', 'heart', 'middle-away',
        'lower-in', 'lower-middle', 'lower-away'
    }
    hot_zones = batter.get('hot_zones', {})
    zone_weights_raw = []
    for zone in ALL_ZONES:
        zw = 10.0
        hot_slg = hot_zones.get(zone, 0.32)
        zone_is_strike = zone in RULEBOOK_STRIKES
        is_chase = not zone_is_strike

        if hot_slg >= 0.5:
            zone_type = 'HOT_ZONE'
        elif hot_slg <= 0.28 or zone in ('lower-away', 'middle-away'):
            zone_type = 'COLD_ZONE'
        elif is_chase:
            zone_type = 'CHASE_ZONE'
        else:
            zone_type = 'NEUTRAL_ZONE'

        if zone_type == 'HOT_ZONE':
            if is_behind and balls == 3 and strikes < 2:
                zw *= 0.7
            else:
                zw *= 0.22
        elif zone_type == 'COLD_ZONE':
            zw *= 2.4

        if is_ahead:
            if is_chase:
                zw *= 3.4
            elif zone == 'heart':
                zw *= 0.12
        elif is_behind:
            if is_chase:
                zw *= 0.12
            else:
                zw *= 2.0

        if is_double_play:
            if zone in ('lower-in', 'lower-middle', 'lower-away'):
                zw *= 3.0
            elif zone == 'chase-low':
                zw *= 2.6
            elif zone in ('upper-in', 'upper-middle', 'upper-away', 'chase-high'):
                zw *= 0.3

        if is_bases_loaded and is_chase:
            zw *= 0.25

        zone_weights_raw.append({'zone': zone, 'zw': zw, 'zone_is_strike': zone_is_strike, 'zone_type': zone_type})

    total_zone_weight = max(sum(x['zw'] for x in zone_weights_raw), 0.001)
    sorted_zones = sorted(zone_weights_raw, key=lambda x: x['zw'], reverse=True)
    ranked_zone_weights = []
    for idx, zw_dict in enumerate(sorted_zones):
        zone = zw_dict['zone']
        zw = zw_dict['zw']
        prob = (zw / total_zone_weight) * 100.0
        ranked_zone_weights.append({
            'zone': zone,
            'weight': round(zw, 1),
            'probability_pct': round(prob, 1),
            'rank': idx + 1,
            'is_strike': zw_dict['zone_is_strike'],
            'zone_type': zw_dict['zone_type'],
            'is_most_likely': (idx == 0),
            'is_least_likely': (idx == len(sorted_zones) - 1)
        })

    top_pitch = ranked_pitch_weights[0]['pitch_name'] if ranked_pitch_weights else arsenal[0]['name']
    top_zone = ranked_zone_weights[0]['zone'] if ranked_zone_weights else 'lower-away'

    pitcher_raw = pitcher.get('throws') or pitcher.get('handedness') or 'R'
    pitcher_hand = 'L' if str(pitcher_raw).upper().startswith('L') else 'R'
    batter_raw = (
        batter.get('handedness')
        or batter.get('bats')
        or (batter.get('vitals') or {}).get('bats')
        or 'R'
    )
    batter_text = str(batter_raw).upper()
    if batter_text.startswith('S'):
        batter_side = 'L' if pitcher_hand == 'R' else 'R'
    else:
        batter_side = 'L' if batter_text.startswith('L') else 'R'
    top_zone = pitch_specific_zone(
        top_zone,
        top_pitch,
        pitcher_hand=pitcher_hand,
        batter_side=batter_side,
    )

    return {
        'strategy_name': strategy_name,
        'situation_tag': situation_tag,
        'count_context': count_context,
        'rationale': rationale,
        'recommended_pitch': top_pitch,
        'recommended_zone': top_zone,
        'pitch_weights': ranked_pitch_weights,
        'zone_weights': ranked_zone_weights,
        'command_quality': 'TARGET_EXECUTED'
    }
