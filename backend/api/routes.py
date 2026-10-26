"""
Authoritative REST API Routes for Baseball Simulation.
Provides strict contract parity with React Native Expo client and Android clients.
"""

import os

from flask import Blueprint, jsonify, request
from typing import Dict, Any

from backend.database.db import get_team_roster_players
from backend.engine.game_engine import GameEngine

api_bp = Blueprint('api', __name__)

team_names = ['New York Yankees', 'New York Mets']


def load_team_roster(team_name: str) -> dict:
    """Queries SQLite via db.py and categorizes hydrated Player objects."""
    players = get_team_roster_players(team_name)

    position_players = [
        p for p in players if p.position not in ('SP', 'RP', 'P', 'CP')
    ]
    starters = [p for p in players if p.position in ('SP', 'P')]
    bullpen = [p for p in players if p.position in ('RP', 'CP')]

    # Fallbacks if database has fewer players
    if not starters and players:
        starters = [players[0]]
    if not position_players and players:
        position_players = players

    return {
        'team_name': team_name,
        'all_players': players,
        'position_players': position_players,
        'pitchers': {
            'starters': starters,
            'bullpen': bullpen,
        },
    }


# Initialize team rosters from database queries
team_rosters = [load_team_roster(name) for name in team_names]
game_engine = None


def get_or_create_engine() -> GameEngine:
    global game_engine, team_rosters
    if game_engine is None:
        away = team_rosters[0]
        home = team_rosters[1]
        game_engine = GameEngine(home, away, team_names[1], team_names[0])
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
    engine = get_or_create_engine()
    game_payload = engine.get_game_state_payload()

    # Build typed lineups and rotations matching InitialStateResponse
    lineups_data = []
    rotations_data = []

    for i, name in enumerate(team_names):
        roster = team_rosters[i]
        lineup_players = []
        for order_idx, p in enumerate(roster['position_players']):
            lineup_players.append({
                'batting_order': order_idx + 1,
                'player': {
                    'id': getattr(p, 'id', order_idx + 1) or (order_idx + 1),
                    'name': p.name,
                    'jersey_number': int(p.number) if str(p.number).isdigit() else 99,
                    'position': p.position,
                    'team': name
                },
                'ratings': f"Power {p.get_rating('Power', 80)} / Contact {p.get_rating('Contact', 80)}" if hasattr(p, 'get_rating') else 'Standard'
            })

        starters_list = []
        for s_idx, sp in enumerate(roster['pitchers']['starters']):
            starters_list.append({
                'id': getattr(sp, 'id', 100 + s_idx) or (100 + s_idx),
                'name': sp.name,
                'jersey_number': int(sp.number) if str(sp.number).isdigit() else 26,
                'position': sp.position,
                'team': name
            })

        bullpen_list = []
        for b_idx, rp in enumerate(roster['pitchers'].get('bullpen', [])):
            bullpen_list.append({
                'id': getattr(rp, 'id', 200 + b_idx) or (200 + b_idx),
                'name': rp.name,
                'jersey_number': int(rp.number) if str(rp.number).isdigit() else 99,
                'position': rp.position,
                'team': name
            })

        lineups_data.append({
            'team_id': i + 1,
            'team_name': name,
            'lineup': lineup_players
        })
        rotations_data.append({
            'team_id': i + 1,
            'team_name': name,
            'starters': starters_list,
            'bullpen': bullpen_list
        })

    return jsonify({
        'teams': team_names,
        'game': game_payload,
        'game_state': game_payload,
        'lineups': lineups_data,
        'rotations': rotations_data
    })


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


def _parse_batter_decision(data: dict):
    decision = data.get('batter_decision')
    if decision is None:
        return None
    normalized = str(decision).upper()
    if normalized not in ('SWING', 'TAKE'):
        raise ValueError("batter_decision must be 'SWING' or 'TAKE'")
    return normalized


@api_bp.route('/api/start_game', methods=['POST'])
def start_game():
    global game_engine, team_rosters
    data = request.get_json(silent=True) or {}
    try:
        seed = _parse_seed(data)
    except ValueError as error:
        return jsonify({'status': 'error', 'message': str(error)}), 400
    # Reload fresh roster state from DB on start
    team_rosters = [load_team_roster(name) for name in team_names]
    away = team_rosters[0]
    home = team_rosters[1]
    game_engine = GameEngine(home, away, team_names[1], team_names[0], seed=seed)
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
    )
    return _pitch_response(outcome, 200 if outcome.get('status') == 'success' else _pitch_error_status(outcome))


@api_bp.route('/api/sim_at_bat', methods=['POST'])
def sim_at_bat():
    engine = get_or_create_engine()
    outcome = engine.sim_at_bat()
    return jsonify(outcome)


@api_bp.route('/api/reset', methods=['POST'])
def reset():
    global game_engine, team_rosters
    data = request.get_json(silent=True) or {}
    try:
        seed = _parse_seed(data)
    except ValueError as error:
        return jsonify({'status': 'error', 'message': str(error)}), 400
    team_rosters = [load_team_roster(name) for name in team_names]
    away = team_rosters[0]
    home = team_rosters[1]
    game_engine = GameEngine(home, away, team_names[1], team_names[0], seed=seed)
    return state()


@api_bp.route('/api/swap_lineup', methods=['POST'])
def swap_lineup():
    data = request.get_json(silent=True) or {}
    team_idx = int(data.get('team', 0))
    pos1 = int(data.get('pos1', 1))
    pos2 = int(data.get('pos2', 2))

    if team_idx < 0 or team_idx >= len(team_rosters):
        return jsonify({'error': 'Invalid team index.'}), 400

    lineup = team_rosters[team_idx]['position_players']
    if min(pos1, pos2) < 1 or max(pos1, pos2) > len(lineup):
        return jsonify({'error': 'Position index out of range.'}), 400

    lineup[pos1 - 1], lineup[pos2 - 1] = lineup[pos2 - 1], lineup[pos1 - 1]
    return jsonify({'status': 'swapped', 'team': team_names[team_idx]})


@api_bp.route('/api/swap_rotation', methods=['POST'])
def swap_rotation():
    data = request.get_json(silent=True) or {}
    team_idx = int(data.get('team', 0))
    pos1 = int(data.get('pos1', 1))
    pos2 = int(data.get('pos2', 2))

    if team_idx < 0 or team_idx >= len(team_rosters):
        return jsonify({'error': 'Invalid team index.'}), 400

    rotation = team_rosters[team_idx]['pitchers']['starters']
    if min(pos1, pos2) < 1 or max(pos1, pos2) > len(rotation):
        return jsonify({'error': 'Rotation index out of range.'}), 400

    rotation[pos1 - 1], rotation[pos2 - 1] = rotation[pos2 - 1], rotation[pos1 - 1]
    return jsonify({'status': 'swapped', 'team': team_names[team_idx]})


@api_bp.route('/api/rosters', methods=['GET'])
def rosters():
    data = {}
    for i, name in enumerate(team_names):
        r = team_rosters[i]
        data[name] = {
            'position_players': [p.__dict__ if hasattr(p, '__dict__') else p for p in r['position_players']],
            'pitchers': {
                'starters': [p.__dict__ if hasattr(p, '__dict__') else p for p in r['pitchers']['starters']],
                'bullpen': [p.__dict__ if hasattr(p, '__dict__') else p for p in r['pitchers']['bullpen']],
            }
        }
    return jsonify(data)
