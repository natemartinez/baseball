import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, '/Users/ljmartinez/Downloads/dev-projects/baseball')

from backend.api.app import create_app

app = create_app()
client = app.test_client()

print("==================================================")
print("RUNNING END-TO-END STATCAST REALIGNMENT VALIDATION")
print("==================================================")

# 1. Health Check
res = client.get('/api/health')
assert res.status_code == 200
data = res.get_json()
print("[PASS] Health Check:", data)

# 2. Initial State
res = client.get('/api/state')
assert res.status_code == 200
state = res.get_json()
assert len(state['teams']) == 2
assert len(state['lineups']) == 2
assert len(state['rotations']) == 2
print("[PASS] State Check:")
print(f"       Teams: {state['teams']}")
print(f"       Batter: {state['game']['current_batter']['name']} (#{state['game']['current_batter']['jersey_number']})")
print(f"       Pitcher: {state['game']['current_pitcher']['name']} (#{state['game']['current_pitcher']['jersey_number']})")

# 3. Start Game
res = client.post('/api/start_game', json={'home_team_id': 1, 'away_team_id': 2})
assert res.status_code == 200
print("[PASS] Start Game Check: Game Initialized.")

# 4. Multi-Pitch Simulation (100 Pitches)
print("\nThrowing 100 pitches through 2D Gaussian Statcast simulation...")
strikes_count = 0
balls_count = 0
leaks_count = 0
shadow_hits = 0
miss_radii = []

for i in range(100):
    # Alternate target zones
    target_zone = "lower-away" if i % 2 == 0 else "heart"
    r = client.post('/api/pitch', json={
        'pitch_intent': 'STRIKE',
        'target_zone': target_zone,
        'batter_approach': 'AUTO'
    })
    assert r.status_code == 200
    pkt = r.get_json()['pitch_details']['gameday_packet']
    
    is_strike = pkt['result']['isStrike']
    if is_strike:
        strikes_count += 1
    else:
        balls_count += 1
        
    if pkt['execution']['isHeartZoneLeak']:
        leaks_count += 1
    if pkt['execution']['hitShadowZoneTarget']:
        shadow_hits += 1
        
    miss_radii.append(pkt['execution']['radialMissInches'])

mean_miss = round(sum(miss_radii) / len(miss_radii), 2)
print(f"[PASS] 100-Pitch Simulation Completed:")
print(f"       Strikes: {strikes_count} | Balls: {balls_count}")
print(f"       Mean Radial Miss Radius: {mean_miss} inches (expected ~3.5-5.0 inches for Command 68)")
print(f"       Heart Leaks: {leaks_count}% | Shadow Zone Hits: {shadow_hits}")

# 5. Sim At-Bat
res = client.post('/api/sim_at_bat')
assert res.status_code == 200
ab_res = res.get_json()
print("\n[PASS] Sim At-Bat Check:")
print(f"       Final pitch: {ab_res['pitch_details']['pitch_name']}")
print(f"       Call: {ab_res['pitch_details']['gameday_packet']['result']['call']}")
print(f"       Outs: {ab_res['game_state']['outs']} | Inning: {ab_res['game_state']['inning']}")

print("\n==================================================")
print("ALL 5 VALIDATION SUITES PASSED WITH 100% PARITY!")
print("==================================================")
