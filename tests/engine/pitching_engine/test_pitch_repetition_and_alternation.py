import pytest
from backend.engine.pitching_engine.pitch_selection.intent import pitch_specific_zone


def test_pitch_specific_zone_backward_compatibility():
    """Existing call signatures with no last pitch arguments remain 100% backward compatible."""
    assert pitch_specific_zone('lower-away', '4-Seam Fastball', 'R', 'R') == 'upper-away'
    assert pitch_specific_zone('upper-middle', '4-Seam Fastball', 'R', 'R') == 'upper-middle'
    assert pitch_specific_zone('heart', 'Power Sinker', 'R', 'R') == 'lower-middle'
    assert pitch_specific_zone('middle-in', 'Power Sinker', 'R', 'R') == 'lower-in'
    assert pitch_specific_zone('lower-away', 'Slider', 'R', 'R') == 'lower-away'


def test_fastball_alternation_when_doubling_up():
    """Doubling up on a fastball toggles horizontal edge corridors."""
    # Base mapping for 4SFB on lower-away is upper-away.
    # If the prior pitch was also 4SFB targeted at upper-away, alternate to upper-in!
    alt_zone = pitch_specific_zone(
        'lower-away',
        '4-Seam Fastball',
        pitcher_hand='R',
        batter_side='R',
        last_pitch_name='4-Seam Fastball',
        last_target_zone='upper-away',
    )
    assert alt_zone == 'upper-in'

    # If prior pitch targeted upper-in, alternate to upper-away
    alt_zone_2 = pitch_specific_zone(
        'lower-away',
        '4-Seam Fastball',
        pitcher_hand='R',
        batter_side='R',
        last_pitch_name='4-Seam Fastball',
        last_target_zone='upper-in',
    )
    assert alt_zone_2 == 'upper-away'


def test_sinker_alternation_when_doubling_up():
    """Doubling up on a sinker toggles arm-side and glove-side lower corners."""
    alt_zone = pitch_specific_zone(
        'lower-away',
        'Power Sinker',
        pitcher_hand='R',
        batter_side='R',
        last_pitch_name='Power Sinker',
        last_target_zone='lower-away',
    )
    assert alt_zone == 'lower-in'

    alt_zone_2 = pitch_specific_zone(
        'lower-away',
        'Power Sinker',
        pitcher_hand='R',
        batter_side='R',
        last_pitch_name='Power Sinker',
        last_target_zone='lower-in',
    )
    assert alt_zone_2 == 'lower-away'


def test_breaking_ball_alternation_when_doubling_up():
    """Doubling up on a breaking ball alternates in-zone locations or chase depths."""
    # When prior pitch was in-zone (lower-away), alternate to lower-in for RHP
    alt_zone = pitch_specific_zone(
        'lower-away',
        'Slider',
        pitcher_hand='R',
        batter_side='R',
        last_pitch_name='Slider',
        last_target_zone='lower-away',
    )
    assert alt_zone == 'lower-in'

    # When prior pitch was chase-away, alternate to chase-low
    alt_zone_chase = pitch_specific_zone(
        'chase-away',
        'Slider',
        pitcher_hand='R',
        batter_side='R',
        last_pitch_name='Slider',
        last_target_zone='chase-away',
    )
    assert alt_zone_chase == 'chase-low'


def test_offspeed_alternation_when_doubling_up():
    """Doubling up on offspeed alternates in-zone bottom zones."""
    alt_zone = pitch_specific_zone(
        'lower-away',
        'Changeup',
        pitcher_hand='R',
        batter_side='R',
        last_pitch_name='Changeup',
        last_target_zone='lower-away',
    )
    assert alt_zone == 'lower-middle'


def test_no_alternation_when_pitch_different():
    """When switching pitches (not doubling up), base pitch specific zone is preserved."""
    zone = pitch_specific_zone(
        'lower-away',
        'Slider',
        pitcher_hand='R',
        batter_side='R',
        last_pitch_name='4-Seam Fastball',
        last_target_zone='upper-away',
    )
    assert zone == 'lower-away'


def test_pitch_strategy_progressive_repetition_decay():
    """Verify progressive decay: 1 consecutive prior throw = 0.75x, 2 consecutive = 0.20x, 3+ = 0.02x."""
    from backend.database.db import get_player
    from backend.engine.pitching_engine.pitch_selection.strategy import PitchStrategy

    pitcher = get_player(1)
    batter = get_player(2)
    strategy = PitchStrategy(pitcher, batter)

    # 0 prior throws
    plan_0 = strategy.build_plan(balls=0, strikes=0, recent_pitches=[])
    prob_0 = plan_0['repertoire_probabilities']['Four-Seam Fastball']

    # 1 prior throw
    plan_1 = strategy.build_plan(balls=0, strikes=0, recent_pitches=['Four-Seam Fastball'])
    prob_1 = plan_1['repertoire_probabilities']['Four-Seam Fastball']
    assert prob_1 < prob_0

    # 2 consecutive prior throws (tripling up should be heavily suppressed)
    plan_2 = strategy.build_plan(balls=0, strikes=0, recent_pitches=['Four-Seam Fastball', 'Four-Seam Fastball'])
    prob_2 = plan_2['repertoire_probabilities']['Four-Seam Fastball']
    assert prob_2 < prob_1 * 0.5  # Distinctly lower than 1 prior throw!

    # 3 consecutive prior throws (quadrupling up should be practically eliminated)
    plan_3 = strategy.build_plan(balls=0, strikes=0, recent_pitches=['Four-Seam Fastball', 'Four-Seam Fastball', 'Four-Seam Fastball'])
    prob_3 = plan_3['repertoire_probabilities']['Four-Seam Fastball']
    assert prob_3 <= 0.05


def test_select_pitch_wires_pitch_sequence_and_alternates_location():
    from backend.database.db import get_player
    from backend.engine.pitching_engine.pitch_selection.selection import select_pitch
    from backend.engine.pitching_engine.pitcher_info.pitch_objects import PitchArsenal
    from backend.engine.pitching_engine.pitch_selection.strategy import PitchStrategy

    pitcher = get_player(1)  # Nolan McLean
    batter = get_player(2)   # Aaron Judge
    arsenal = PitchArsenal.extract_from_pitcher(pitcher)
    strategy = PitchStrategy(pitcher, batter)

    # In user selection mode with Four-Seam Fastball and no explicit target/intent,
    # doubling up on upper-away should automatically alternate to upper-in
    selection = select_pitch(
        strategy=strategy,
        arsenal=arsenal,
        balls=0,
        strikes=0,
        selection_mode='user',
        pitch_name='Four-Seam Fastball',
        pitch_sequence=[{
            'pitch_name': 'Four-Seam Fastball',
            'target_zone': 'upper-away',
            'zone_name': 'upper-away',
        }],
        rng=lambda: 0.99,
    )

    assert selection.recommended_zone == 'upper-in'
    assert selection.target_intent.nominal_zone == 'upper-in'


def test_game_engine_location_alternation_on_consecutive_same_pitches():
    """Verify that GameEngine passes pitch_sequence through and alternates target zones when repeating a pitch."""
    from backend.database.db import get_player
    from backend.engine.game_engine.engine import GameEngine

    pitcher = get_player(1)
    batter = get_player(2)
    home = {'name': 'Home', 'position_players': [batter], 'pitchers': {'starters': [pitcher], 'bullpen': []}}
    away = {'name': 'Away', 'position_players': [batter], 'pitchers': {'starters': [pitcher], 'bullpen': []}}

    game = GameEngine(home, away, 'Home', 'Away', seed=10)

    # Throw a pitch with Four-Seam Fastball (user selection without explicit target)
    res1 = game.pitch(selection_mode='user', pitch_name='Four-Seam Fastball')
    zone1 = res1['pitch_details']['intended_zone']

    # Throw another pitch with Four-Seam Fastball in the same at-bat
    res2 = game.pitch(selection_mode='user', pitch_name='Four-Seam Fastball')
    zone2 = res2['pitch_details']['intended_zone']

    # Because res1 targeted Four-Seam Fastball at zone1, res2 must alternate and not equal zone1
    assert zone2 != zone1


def test_calculate_strategy_and_intent_adapts_with_pitch_sequence():
    """Verify calculate_strategy_and_intent receives pitch_sequence and decays repeated pitches."""
    from backend.database.db import get_player
    from backend.engine.pitching_engine.pitch_selection.strategy import calculate_strategy_and_intent

    pitcher = get_player(1)  # Nolan McLean
    batter = get_player(2)   # Aaron Judge

    # Pitch 1 (empty sequence) on 2-2 count recommends putaway Sweeper
    rec_0 = calculate_strategy_and_intent(
        outs=0,
        balls=2,
        strikes=2,
        bases={},
        batter=batter,
        pitcher=pitcher,
        pitch_sequence=[],
    )
    assert rec_0['recommended_pitch'] == 'Spin Monster Sweeper'

    # Pitch 2 (after 1 Sweeper thrown) should immediately pivot away to another pitch
    rec_1 = calculate_strategy_and_intent(
        outs=0,
        balls=2,
        strikes=2,
        bases={},
        batter=batter,
        pitcher=pitcher,
        pitch_sequence=[{
            'pitch_name': 'Spin Monster Sweeper',
            'target_zone': 'chase-away',
        }],
    )
    assert rec_1['recommended_pitch'] != 'Spin Monster Sweeper'
    assert rec_1['recommended_pitch'] == 'Spike Curveball'

    # Pitch 3 (after 2 consecutive Sweepers)
    rec_2 = calculate_strategy_and_intent(
        outs=0,
        balls=2,
        strikes=2,
        bases={},
        batter=batter,
        pitcher=pitcher,
        pitch_sequence=[
            {'pitch_name': 'Spin Monster Sweeper', 'target_zone': 'chase-away'},
            {'pitch_name': 'Spin Monster Sweeper', 'target_zone': 'chase-low'},
        ],
    )
    sweeper_w = next(p['probability_pct'] for p in rec_2['pitch_weights'] if p['pitch_name'] == 'Spin Monster Sweeper')
    assert sweeper_w < 15.0
    assert rec_2['recommended_pitch'] != 'Spin Monster Sweeper'


def test_two_two_count_tactical_setup():
    """Verify 2-2 count is treated as TWO_TWO_BATTLE with shadow zone targeting and live fastballs."""
    from backend.database.db import get_player
    from backend.engine.pitching_engine.pitch_selection.strategy import PitchStrategy

    pitcher = get_player(1)  # Nolan McLean
    batter = get_player(2)   # Aaron Judge
    strat = PitchStrategy(pitcher, batter)

    assert strat.get_leverage_state(balls=2, strikes=2) == 'TWO_TWO_COUNT'
    assert strat.get_leverage_state(balls=0, strikes=2) == 'AHEAD_TWO_STRIKES'
    assert strat.get_leverage_state(balls=1, strikes=2) == 'AHEAD_TWO_STRIKES'

    plan = strat.build_plan(balls=2, strikes=2)
    assert plan['strategy_name'] == 'TWO_TWO_BATTLE'
    assert 'Ahead in count' not in plan['rationale']
    assert plan['recommended_zone'] == 'chase-away'
    probs = plan['repertoire_probabilities']
    assert probs['Four-Seam Fastball'] >= 0.08
    assert probs['Power Sinker'] >= 0.08


def test_judge_mclean_at_bat_prevents_four_consecutive_sweepers():
    """Verify that in an at-bat against Aaron Judge, GameEngine recommendations dynamically adapt and prevent repeating sweepers."""
    from backend.database.db import get_player
    from backend.engine.game_engine.engine import GameEngine

    pitcher = get_player(1)  # Nolan McLean
    batter = get_player(2)   # Aaron Judge
    home = {'name': 'Home', 'position_players': [batter], 'pitchers': {'starters': [pitcher], 'bullpen': []}}
    away = {'name': 'Away', 'position_players': [batter], 'pitchers': {'starters': [pitcher], 'bullpen': []}}

    game = GameEngine(home, away, 'Home', 'Away', seed=42)
    game.balls = 2
    game.strikes = 2

    # Pitch 1 recommendation (initial 2-2 count)
    rec1 = game.calculate_strategy_and_intent()
    assert rec1['strategy_name'] == 'TWO_TWO_BATTLE'
    assert rec1['recommended_pitch'] == 'Spin Monster Sweeper'
    assert rec1['recommended_zone'] == 'chase-away'

    # Pitch 1 thrown as Sweeper (recorded in current_at_bat_pitches)
    game.current_at_bat_pitches.append({
        'pitch_name': 'Spin Monster Sweeper',
        'target_zone': rec1['recommended_zone'],
        'zone_name': rec1['recommended_zone'],
    })

    # Pitch 2 recommendation must immediately pivot away from Sweeper!
    rec2 = game.calculate_strategy_and_intent()
    assert rec2['recommended_pitch'] != 'Spin Monster Sweeper'
    assert rec2['recommended_pitch'] == 'Spike Curveball'

    # Pitch 2 thrown as Sweeper anyway
    game.current_at_bat_pitches.append({
        'pitch_name': 'Spin Monster Sweeper',
        'target_zone': 'lower-in',
        'zone_name': 'lower-in',
    })

    # Pitch 3 recommendation must strongly suppress Sweeper (< 15%)
    rec3 = game.calculate_strategy_and_intent()
    assert rec3['recommended_pitch'] != 'Spin Monster Sweeper'
    sweeper_w3 = next(p['probability_pct'] for p in rec3['pitch_weights'] if p['pitch_name'] == 'Spin Monster Sweeper')
    assert sweeper_w3 < 15.0

    # Pitch 3 thrown as Sweeper anyway
    game.current_at_bat_pitches.append({
        'pitch_name': 'Spin Monster Sweeper',
        'target_zone': 'lower-away',
        'zone_name': 'lower-away',
    })

    # Pitch 4 recommendation: Sweeper is practically eliminated (< 3%)
    rec4 = game.calculate_strategy_and_intent()
    assert rec4['recommended_pitch'] != 'Spin Monster Sweeper'
    sweeper_w4 = next(p['probability_pct'] for p in rec4['pitch_weights'] if p['pitch_name'] == 'Spin Monster Sweeper')
    assert sweeper_w4 < 3.0




