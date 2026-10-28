"""
Authoritative REST API Routes for Baseball Simulation.
Provides strict contract parity with React Native Expo client and Android clients.
"""

import os
import math

from flask import Blueprint, jsonify, request
from typing import Dict, Any, Optional, List, Tuple

from backend.database.db import (
    get_all_teams,
    get_team_by_id_or_name,
    get_team_roster_players,
)
from backend.engine.game_engine import GameEngine, PitchFlowError

api_bp = Blueprint('api', __name__)

game_engine = None
current_home_roster = None
current_away_roster = None


def load_team_roster(team_identifier: Any, season: int = 2026) -> dict:
    """Queries SQLite via db.py and categorizes hydrated Player objects using roster metadata."""
    team = get_team_by_id_or_name(team_identifier)
    if not team:
        team_name = str(team_identifier)
        team_id = 1
    else:
        team_name = team['name']
        team_id = team['id']

    players = get_team_roster_players(team_name, season=season)

    # Separate position players from pitchers using is_pitcher and role/position
    position_players = [
        p for p in players if p.position not in ('SP', 'RP', 'P', 'CP') and not p.is_pitcher
    ]
    starters = [
        p for p in players if p.is_pitcher and (getattr(p, 'role', None) == 'starter' or p.position in ('SP', 'P'))
    ]
    bullpen = [
        p for p in players if p.is_pitcher and (getattr(p, 'role', None) == 'bullpen' or p.position in ('RP', 'CP'))
    ]

    # Fallbacks if database has fewer players
    if not starters and players:
        pitchers = [p for p in players if p.is_pitcher]
        starters = pitchers[:1] if pitchers else [players[0]]
    if not position_players and players:
        position_players = players

    # Sort position players by batting_order ASC (non-ordered placed at the bottom)
    position_players.sort(
        key=lambda p: (
            getattr(p, 'batting_order', None) is None,
            getattr(p, 'batting_order', 999) or 999,
            p.name,
        )
    )

    return {
        'team_id': team_id,
        'team_name': team_name,
        'all_players': players,
        'position_players': position_players,
        'pitchers': {
            'starters': starters,
            'bullpen': bullpen,
        },
    }


def get_or_create_engine() -> GameEngine:
    global game_engine, current_home_roster, current_away_roster
    if game_engine is None:
        teams = get_all_teams()
        home_team = teams[0] if len(teams) > 0 else {'id': 1, 'name': 'New York Mets'}
        away_team = teams[1] if len(teams) > 1 else {'id': 2, 'name': 'New York Yankees'}

        current_home_roster = load_team_roster(home_team['id'])
        current_away_roster = load_team_roster(away_team['id'])

        game_engine = GameEngine(
            current_home_roster,
            current_away_roster,
            current_home_roster['team_name'],
            current_away_roster['team_name'],
        )
    return game_engine


@api_bp.route('/')
def index():
    """API-only root; the client UI is served separately by Expo."""
    return jsonify({
        'status': 'ok',
        'service': 'baseball-simulation-api',
        'message': 'REST API only. Start the Expo client for the UI.',
        'health': '/api/health',
    })


@api_bp.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'engine': 'python-statcast-v4.8',
        'port': int(os.environ.get('PORT', '5050')),
        'active_game': game_engine is not None
    })


@api_bp.route('/api/state', methods=['GET'])
def state():
    return jsonify(_build_state_payload())


def _build_state_payload(engine=None):
    engine = engine or get_or_create_engine()
    game_payload = engine.get_game_state_payload()

    teams = get_all_teams()
    lineups_data = []
    rotations_data = []

    for t in teams:
        team_id = t['id']
        team_name = t['name']

        # Use current in-memory roster if active game matches, else load fresh
        if current_home_roster and current_home_roster.get('team_id') == team_id:
            roster = current_home_roster
        elif current_away_roster and current_away_roster.get('team_id') == team_id:
            roster = current_away_roster
        else:
            roster = load_team_roster(team_id)

        lineup_players = []
        for order_idx, p in enumerate(roster['position_players']):
            order_num = getattr(p, 'batting_order', None) or (order_idx + 1)
            power_val = int(p.get_rating('Power', 80)) if hasattr(p, 'get_rating') else 80
            contact_val = int(p.get_rating('Contact', 80)) if hasattr(p, 'get_rating') else 80
            lineup_players.append({
                'batting_order': order_num,
                'player': {
                    'id': getattr(p, 'id', order_idx + 1) or (order_idx + 1),
                    'name': p.name,
                    'jersey_number': int(p.number) if str(p.number).isdigit() else 99,
                    'position': p.position,
                    'team': team_name,
                },
                'ratings': f"Power {power_val} / Contact {contact_val}"
            })

        starters_list = []
        for s_idx, sp in enumerate(roster['pitchers']['starters']):
            starters_list.append({
                'id': getattr(sp, 'id', 100 + s_idx) or (100 + s_idx),
                'name': sp.name,
                'jersey_number': int(sp.number) if str(sp.number).isdigit() else 26,
                'position': sp.position,
                'team': team_name,
            })

        bullpen_list = []
        for b_idx, rp in enumerate(roster['pitchers'].get('bullpen', [])):
            bullpen_list.append({
                'id': getattr(rp, 'id', 200 + b_idx) or (200 + b_idx),
                'name': rp.name,
                'jersey_number': int(rp.number) if str(rp.number).isdigit() else 99,
                'position': rp.position,
                'team': team_name,
            })

        lineups_data.append({
            'team_id': team_id,
            'team_name': team_name,
            'lineup': lineup_players,
        })
        rotations_data.append({
            'team_id': team_id,
            'team_name': team_name,
            'starters': starters_list,
            'bullpen': bullpen_list,
        })

    return {
        'teams': [t['name'] for t in teams],
        'game': game_payload,
        'game_state': game_payload,
        'lineups': lineups_data,
        'rotations': rotations_data,
    }


def _parse_seed(data: dict):
    seed = data.get('seed')
    if seed is None:
        return None
    try:
        return int(seed)
    except (TypeError, ValueError) as error:
        raise ValueError('seed must be an integer') from error


def _parse_pitch_request(data: dict) -> dict:
    pitch_intent = data.get('pitch_intent')
    pitch_type = data.get('pitch_type') or data.get('pitch_name')
    target_zone = data.get('target_zone')
    batter_approach = data.get('batter_approach', 'AUTO')

    custom_target = None
    if 'target_x' in data and 'target_z' in data:
        try:
            custom_target = {
                'x': float(data['target_x']),
                'z': float(data['target_z'])
            }
        except (TypeError, ValueError) as error:
            raise ValueError('target_x and target_z must be numbers') from error

    return {
        'pitch_intent': pitch_intent,
        'pitch_type': pitch_type,
        'target_zone': target_zone,
        'custom_target': custom_target,
        'batter_approach': batter_approach,
    }


def _pitch_response(outcome: dict, status_code: int = 200):
    return jsonify(outcome), status_code


def _pitch_error_status(outcome: dict) -> int:
    message = str(outcome.get('message', '')).lower()
    if 'in flight' in message:
        return 409
    return 400


def _parse_practice_pitch_request(data: dict) -> dict:
    pitch_type = data.get('pitch_type') or data.get('pitch_name')
    if not pitch_type:
        raise ValueError('pitch_type is required for practice pitches')
    if 'target_x' not in data or 'target_z' not in data:
        raise ValueError('target_x and target_z are required for practice pitches')
    try:
        target_x = float(data['target_x'])
        target_z = float(data['target_z'])
    except (TypeError, ValueError) as error:
        raise ValueError('target_x and target_z must be numbers') from error
    if not math.isfinite(target_x) or not math.isfinite(target_z):
        raise ValueError('target_x and target_z must be finite')

    return {
        'pitch_type': str(pitch_type),
        'target_zone': data.get('target_zone'),
        'custom_target': {'x': target_x, 'z': target_z},
    }


def _parse_batter_decision(data: dict):
    decision = data.get('batter_decision')
    if decision is None:
        return None
    normalized = str(decision).upper()
    if normalized not in ('SWING', 'TAKE'):
        raise ValueError("batter_decision must be 'SWING' or 'TAKE'")
    return normalized


def _parse_contact(data: dict):
    """
    Parses a Rapier contact report.

    Invalid or non-finite contact data degrades to a swing miss so a malformed
    client payload never loses or corrupts a pending pitch.
    """
    raw = data.get('contact')
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return {'contacted': False}
    if not bool(raw.get('contacted')):
        return {'contacted': False}

    def finite(key):
        try:
            value = float(raw.get(key))
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value):
            return None
        return value

    exit_velocity = finite('exit_velocity_mph')
    launch_angle = finite('launch_angle_deg')
    spray_angle = finite('spray_angle_deg')
    if exit_velocity is None or launch_angle is None or spray_angle is None:
        return {'contacted': False}

    report = {
        'contacted': True,
        'exit_velocity_mph': max(45.0, min(122.0, exit_velocity)),
        'launch_angle_deg': max(-25.0, min(78.0, launch_angle)),
        'spray_angle_deg': max(-65.0, min(65.0, spray_angle)),
    }

    for key in ('contact_offset_ft', 'bat_speed_mph', 'charge', 'timing_offset_ms'):
        value = finite(key)
        if value is not None:
            report[key] = value
    return report


@api_bp.route('/api/start_game', methods=['POST'])
def start_game():
    global game_engine, current_home_roster, current_away_roster
    data = request.get_json(silent=True) or {}
    try:
        seed = _parse_seed(data)
    except ValueError as error:
        return jsonify({'status': 'error', 'message': str(error)}), 400

    teams = get_all_teams()
    # Default to 1 (Home: Mets) and 2 (Away: Yankees) if not specified
    home_id = data.get('home_team_id') or (teams[0]['id'] if teams else 1)
    away_id = data.get('away_team_id') or (teams[1]['id'] if len(teams) > 1 else 2)

    current_home_roster = load_team_roster(home_id)
    current_away_roster = load_team_roster(away_id)

    game_engine = GameEngine(
        current_home_roster,
        current_away_roster,
        home_name=current_home_roster['team_name'],
        away_name=current_away_roster['team_name'],
        seed=seed,
    )
    payload = game_engine.get_game_state_payload()
    return jsonify(payload)


@api_bp.route('/api/pitch', methods=['POST'])
def pitch():
    engine = get_or_create_engine()
    data = request.get_json(silent=True) or {}
    try:
        options = _parse_pitch_request(data)
    except ValueError as error:
        return jsonify({'status': 'error', 'message': str(error)}), 400

    outcome = engine.pitch(
        pitch_intent=options['pitch_intent'],
        pitch_type=options['pitch_type'],
        target_zone=options['target_zone'],
        custom_target=options['custom_target'],
        batter_approach=options['batter_approach']
    )
    return jsonify(outcome)


@api_bp.route('/api/pitch/throw', methods=['POST'])
def throw_pitch():
    engine = get_or_create_engine()
    data = request.get_json(silent=True) or {}
    try:
        options = _parse_pitch_request(data)
    except ValueError as error:
        return jsonify({'status': 'error', 'message': str(error)}), 400

    outcome = engine.throw_pitch(
        pitch_intent=options['pitch_intent'],
        pitch_type=options['pitch_type'],
        target_zone=options['target_zone'],
        custom_target=options['custom_target'],
    )
    return _pitch_response(outcome, 200 if outcome.get('status') == 'success' else _pitch_error_status(outcome))


@api_bp.route('/api/pitch/resolve', methods=['POST'])
def resolve_pitch():
    engine = get_or_create_engine()
    data = request.get_json(silent=True) or {}
    try:
        batter_decision = _parse_batter_decision(data)
    except ValueError as error:
        return jsonify({'status': 'error', 'message': str(error)}), 400

    outcome = engine.resolve_pitch(
        batter_approach=data.get('batter_approach', 'AUTO'),
        batter_decision=batter_decision,
        contact=_parse_contact(data),
    )
    return _pitch_response(outcome, 200 if outcome.get('status') == 'success' else _pitch_error_status(outcome))


@api_bp.route('/api/practice/start', methods=['POST'])
def start_practice():
    engine = get_or_create_engine()
    try:
        engine.start_practice()
    except PitchFlowError as error:
        return jsonify({'status': 'error', 'message': str(error)}), 409
    return jsonify(_build_state_payload(engine))


@api_bp.route('/api/practice/pitch/throw', methods=['POST'])
def practice_throw_pitch():
    engine = get_or_create_engine()
    data = request.get_json(silent=True) or {}
    try:
        options = _parse_practice_pitch_request(data)
    except ValueError as error:
        return jsonify({'status': 'error', 'message': str(error)}), 400

    outcome = engine.practice_throw_pitch(
        pitch_type=options['pitch_type'],
        target_zone=options['target_zone'],
        custom_target=options['custom_target'],
    )
    return _pitch_response(
        outcome,
        200 if outcome.get('status') == 'success' else _pitch_error_status(outcome),
    )


@api_bp.route('/api/practice/pitch/resolve', methods=['POST'])
def practice_resolve_pitch():
    engine = get_or_create_engine()
    data = request.get_json(silent=True) or {}
    try:
        batter_decision = _parse_batter_decision(data)
    except ValueError as error:
        return jsonify({'status': 'error', 'message': str(error)}), 400

    outcome = engine.practice_resolve_pitch(
        batter_approach=data.get('batter_approach', 'AUTO'),
        batter_decision=batter_decision,
        contact=_parse_contact(data),
    )
    return _pitch_response(
        outcome,
        200 if outcome.get('status') == 'success' else _pitch_error_status(outcome),
    )


@api_bp.route('/api/practice/end', methods=['POST'])
def end_practice():
    engine = get_or_create_engine()
    engine.end_practice()
    return jsonify(_build_state_payload(engine))


@api_bp.route('/api/sim_at_bat', methods=['POST'])
def sim_at_bat():
    engine = get_or_create_engine()
    outcome = engine.sim_at_bat()
    return jsonify(outcome)


def _resolve_target_roster(team_param: Any) -> Optional[dict]:
    """Resolves target team roster by DB team_id, team_name, or index."""
    if team_param is None:
        return current_home_roster

    active_rosters = [r for r in [current_home_roster, current_away_roster] if r]
    # Check by team_id
    for r in active_rosters:
        if str(r.get('team_id')) == str(team_param):
            return r
    # Check by team_name
    for r in active_rosters:
        if r.get('team_name', '').lower() == str(team_param).lower():
            return r

    # Match by DB team lookup
    team = get_team_by_id_or_name(team_param)
    if team:
        for r in active_rosters:
            if r.get('team_name') == team['name']:
                return r

    # Fallback to index
    try:
        idx = int(team_param)
        if 0 <= idx < len(active_rosters):
            return active_rosters[idx]
        if 1 <= idx <= len(active_rosters):
            return active_rosters[idx - 1]
    except (ValueError, TypeError):
        pass

    return None


@api_bp.route('/api/reset', methods=['POST'])
def reset():
    global game_engine, current_home_roster, current_away_roster
    data = request.get_json(silent=True) or {}
    try:
        seed = _parse_seed(data)
    except ValueError as error:
        return jsonify({'status': 'error', 'message': str(error)}), 400

    teams = get_all_teams()
    home_id = data.get('home_team_id') or (current_home_roster.get('team_id') if current_home_roster else (teams[0]['id'] if teams else 1))
    away_id = data.get('away_team_id') or (current_away_roster.get('team_id') if current_away_roster else (teams[1]['id'] if len(teams) > 1 else 2))

    current_home_roster = load_team_roster(home_id)
    current_away_roster = load_team_roster(away_id)

    game_engine = GameEngine(
        current_home_roster,
        current_away_roster,
        home_name=current_home_roster['team_name'],
        away_name=current_away_roster['team_name'],
        seed=seed,
    )
    return state()


@api_bp.route('/api/swap_lineup', methods=['POST'])
def swap_lineup():
    data = request.get_json(silent=True) or {}
    team_param = data.get('team')
    pos1 = int(data.get('pos1', 1))
    pos2 = int(data.get('pos2', 2))

    roster = _resolve_target_roster(team_param)
    if not roster:
        return jsonify({'error': f'Invalid team identifier: {team_param}'}), 400

    lineup = roster['position_players']
    if min(pos1, pos2) < 1 or max(pos1, pos2) > len(lineup):
        return jsonify({'error': 'Position index out of range.'}), 400

    lineup[pos1 - 1], lineup[pos2 - 1] = lineup[pos2 - 1], lineup[pos1 - 1]

    # Synchronize batting_order attributes if present
    p1, p2 = lineup[pos1 - 1], lineup[pos2 - 1]
    if hasattr(p1, 'batting_order') and hasattr(p2, 'batting_order'):
        p1.batting_order, p2.batting_order = pos1, pos2

    # Synchronize active game engine lineup
    if game_engine:
        if roster.get('team_name') == game_engine.home_name:
            game_engine.home_lineup = [game_engine._ensure_player(p) for p in lineup]
        elif roster.get('team_name') == game_engine.away_name:
            game_engine.away_lineup = [game_engine._ensure_player(p) for p in lineup]

    return jsonify({'status': 'swapped', 'team': roster['team_name']})


@api_bp.route('/api/swap_rotation', methods=['POST'])
def swap_rotation():
    data = request.get_json(silent=True) or {}
    team_param = data.get('team')
    pos1 = int(data.get('pos1', 1))
    pos2 = int(data.get('pos2', 2))

    roster = _resolve_target_roster(team_param)
    if not roster:
        return jsonify({'error': f'Invalid team identifier: {team_param}'}), 400

    rotation = roster['pitchers']['starters']
    if min(pos1, pos2) < 1 or max(pos1, pos2) > len(rotation):
        return jsonify({'error': 'Rotation index out of range.'}), 400

    rotation[pos1 - 1], rotation[pos2 - 1] = rotation[pos2 - 1], rotation[pos1 - 1]

    # Synchronize active game engine pitcher
    if game_engine and len(rotation) > 0:
        if roster.get('team_name') == game_engine.home_name:
            game_engine.home_pitcher = game_engine._ensure_player(rotation[0])
        elif roster.get('team_name') == game_engine.away_name:
            game_engine.away_pitcher = game_engine._ensure_player(rotation[0])

    return jsonify({'status': 'swapped', 'team': roster['team_name']})


@api_bp.route('/api/teams', methods=['GET'])
def get_teams():
    """Returns all registered teams from SQLite (Approach B: Franchise / Scheduling)."""
    teams = get_all_teams()
    return jsonify({
        'status': 'ok',
        'teams': teams,
        'count': len(teams)
    })


@api_bp.route('/api/rosters', methods=['GET'])
def rosters():
    """Returns active rosters from SQLite, optionally filtered by team_id or team_name."""
    team_id = request.args.get('team_id')
    team_name = request.args.get('team') or request.args.get('team_name')
    season = int(request.args.get('season', 2026))

    if team_id or team_name:
        target = team_id or team_name
        r = load_team_roster(target, season=season)
        return jsonify({
            'team_id': r['team_id'],
            'team_name': r['team_name'],
            'season': season,
            'position_players': [p.to_dict() if hasattr(p, 'to_dict') else p for p in r['position_players']],
            'pitchers': {
                'starters': [p.to_dict() if hasattr(p, 'to_dict') else p for p in r['pitchers']['starters']],
                'bullpen': [p.to_dict() if hasattr(p, 'to_dict') else p for p in r['pitchers']['bullpen']],
            }
        })

    teams = get_all_teams()
    data = {}
    for t in teams:
        r = load_team_roster(t['id'], season=season)
        data[t['name']] = {
            'team_id': t['id'],
            'position_players': [p.to_dict() if hasattr(p, 'to_dict') else p for p in r['position_players']],
            'pitchers': {
                'starters': [p.to_dict() if hasattr(p, 'to_dict') else p for p in r['pitchers']['starters']],
                'bullpen': [p.to_dict() if hasattr(p, 'to_dict') else p for p in r['pitchers']['bullpen']],
            }
        }
    return jsonify(data)
