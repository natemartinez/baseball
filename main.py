from flask import Flask, render_template, request, jsonify
from roster import rosters
from backend.game_engine import GameEngine

app = Flask(__name__)

team_names = ["New York Yankees", "New York Mets"]
team_rosters = [rosters['away_team'], rosters['home_team']]
game_engine = None # initializes with no game played -> waiting for start_game


@app.route('/')
def index():
    return render_template('index.html', teams=team_names)


@app.route('/api/state')
def state():
    data = {
        'teams': team_names,
        'game': None,
        'lineups': [],
        'rotations': []
    }
    for i, name in enumerate(team_names):
        roster = team_rosters[i]
        lineup = [f"{p.number} {p.name} - {p.position}" for p in roster['position_players']]
        rotation = [f"{p.number} {p.name} - {p.position}" for p in roster['pitchers']['starters']]
        data['lineups'].append({'name': name, 'players': lineup})
        data['rotations'].append({'name': name, 'pitchers': rotation})

    if game_engine: # if the game's engine is loaded in:
        data['game'] = {
            'inning': game_engine.inning,
            'top_bottom': game_engine.top_bottom,
            'score': dict(game_engine.score),
            'outs': game_engine.outs,
            'balls': game_engine.balls,
            'strikes': game_engine.strikes,
            'bases': dict(game_engine.bases),
            'batter': game_engine.current_batter().name,
            'pitcher': game_engine.current_pitcher_obj().name,
            'game_over': game_engine.game_over
        }
    return jsonify(data)


@app.route('/api/start_game', methods=['POST'])
def start_game():
    global game_engine
    away = team_rosters[0]
    home = team_rosters[1]
    game_engine = GameEngine(home, away, team_names[1], team_names[0])
    return jsonify({'status': 'started'})


@app.route('/api/pitch', methods=['POST'])
def pitch():
    global game_engine
    if not game_engine:
        return jsonify({'error': 'Start a game first.'}), 400
    result, (outs, balls, strikes) = game_engine.pitch() # Expects this from the pitch() in the backend 
    return jsonify({'result': result, 'outs': outs, 'balls': balls, 'strikes': strikes})


@app.route('/api/reset', methods=['POST'])
def reset():
    global game_engine
    away = team_rosters[0]
    home = team_rosters[1]
    game_engine = GameEngine(home, away, team_names[1], team_names[0])
    return jsonify({'status': 'reset'})


@app.route('/api/swap_lineup', methods=['POST'])
def swap_lineup():
    data = request.get_json()
    team_idx = int(data['team'])
    pos1 = int(data['pos1'])
    pos2 = int(data['pos2'])
    lineup = team_rosters[team_idx]['position_players']
    lineup[pos1 - 1], lineup[pos2 - 1] = lineup[pos2 - 1], lineup[pos1 - 1]
    return jsonify({'status': 'swapped'})


@app.route('/api/swap_rotation', methods=['POST'])
def swap_rotation():
    data = request.get_json()
    team_idx = int(data['team'])
    pos1 = int(data['pos1'])
    pos2 = int(data['pos2'])
    rotation = team_rosters[team_idx]['pitchers']['starters']
    rotation[pos1 - 1], rotation[pos2 - 1] = rotation[pos2 - 1], rotation[pos1 - 1]
    return jsonify({'status': 'swapped'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
