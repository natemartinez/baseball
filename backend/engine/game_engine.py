import os
import sys
import random

# Ensure repository root is in sys.path so backend package imports work in all contexts
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from backend.engine.pitch_strategy import PitchStrategyMVP
    from backend.engine.batter_strategy import BatterStrategy
    from backend.engine.strike_zone import StrikeZone
except ImportError:
    from pitch_strategy import PitchStrategyMVP
    from batter_strategy import BatterStrategy
    from backend.engine.strike_zone import StrikeZone
# expects to work with home_roster, away_roster, home_name, away_name as dict
class GameEngine:
    def __init__(self, home_roster, away_roster, home_name, away_name):

        self.home_roster = home_roster
        self.away_roster = away_roster
        self.home_name = home_name
        self.away_name = away_name

        # Game state - Pitch() function uses self to manipulate self.inning-> game_over
        self.inning = 1
        self.outs = 0
        self.top_bottom = "top"  # top = away bats, bottom = home bats
        self.score = {self.away_name: 0, self.home_name: 0}
        self.balls = 0
        self.strikes = 0
        self.game_over = False
        self.strike_zone = StrikeZone()
        # Strike Zone defined by coordinates
        # Split into two different dictionaries
        # CATCHER'S POV = Pitch Up & In should land on the (0,0):Top-Left
        self.pitch_strategy = self.strategy = PitchStrategyMVP()
        self.batter_strategy = BatterStrategy()

        # Bases: 0=empty, 1=runner on 1st, 2=2nd, 3=3rd, 4=1st&2nd, 5=1st&3rd, 6=2nd&3rd, 7=loaded
        # Using a simple dict for clarity
        self.bases = {1: False, 2: False, 3: False}

        # Batting order
        self.away_lineup = away_roster['position_players'][:]
        self.home_lineup = home_roster['position_players'][:]
        self.current_batter_index = 0


        # Starting pitchers
        self.away_pitcher = away_roster['pitchers']['starters'][0]
        self.home_pitcher = home_roster['pitchers']['starters'][0]


    def current_batter_obj(self):
        if self.top_bottom == "top":
            return self.away_lineup[self.current_batter_index]
        else:
            return self.home_lineup[self.current_batter_index]

    def current_batter(self):
        return self.current_batter_obj()

    def current_pitcher_obj(self):
        if self.top_bottom == "top":
            return self.home_pitcher
        else:
            return self.away_pitcher

    def advance_batter(self):
        lineup = self.away_lineup if self.top_bottom == "top" else self.home_lineup
        lineup_len = len(lineup) if lineup else 9
        self.current_batter_index = (self.current_batter_index + 1) % lineup_len

    def _reset_count(self):
        self.balls = 0
        self.strikes = 0

    def _clear_bases(self):
        self.bases = {1: False, 2: False, 3: False}

    def _runners_on_base_count(self):
        return sum(self.bases.values())

    def _advance_runners(self, bases_advanced):
        """
        Move all runners forward by `bases_advanced` (1,2,3,4 for HR).
        Returns number of runs scored.
        """
        runs = 0
        # Start from 3rd base moving up
        for base in [3,2,1]:
            if self.bases[base]:
                new_base = base + bases_advanced
                if new_base >= 4:
                    runs += 1
                    self.bases[base] = False
                else:
                    self.bases[base] = False
                    self.bases[new_base] = True
        return runs

    def _place_batter_on_base(self, bases_taken):
        """
        Place batter on a base after a hit/walk. 
        bases_taken: 1 (single), 2 (double), 3 (triple), 4 (home run)
        Advances existing runners accordingly.
        Returns runs scored.
        """
        runs = 0
        # First, advance existing runners by bases_taken
        runs += self._advance_runners(bases_taken)
        # Then place batter on base if not a home run
        if bases_taken < 4:
            self.bases[bases_taken] = True
        # For home run, batter scores a run
        if bases_taken == 4:
            runs += 1
        return runs


    # ====================================================================
    # PITCH INTENT / DECISION-MAKING LAYER
    #   pitch_choice          -> WHICH pitch (a Pitch instance)
    #   _matchup_target       -> relative label for the handedness matchup
    #   _pick_intended_target -> (zone grid, label) the pitcher WANTS
    #   pitch_location        -> orchestrator: intent + dice rolls
    #
    # These four compose the decision layer: they decide *what* to throw and
    # *where* the pitcher intends it to go. Nothing here resolves a final
    # coordinate — the intent dict they produce is handed to pitch_to_zone
    # (EXECUTION) below.
    # ====================================================================

    def pitch_choice(self):
        """Strategic pitch selection: count leverage -> weights -> category -> Pitch."""
        # WEIGHTS ARE STORED IN _init_ function inside pitch_strategy.py
        def _pitch_randomizer(strategy):
            # Return string after randomizer -> direct lookup to the pitch object
              pitch_selection = list(strategy["weights"].keys())
              weights = list(strategy["weights"].values()) 

              return random.choices(pitch_selection, weights=weights, k=1)[0]

        leverage, probs = self.strategy.calculate_probabilities(
            self.balls, self.strikes,
            double_play_situation=(self.outs < 2 and self.bases[1]))
        
        chosen_type = self.strategy.select_pitch(probs)

        self._last_strategy = {"leverage": leverage, "weights": probs, "category": chosen_type}

        # last_strategy -> Randomizer -> Chosen Pitch
        #print('LAST STRATEGY:',self._last_strategy)

        return _pitch_randomizer(self._last_strategy)



    def pitch_intent_manager(self, pitch, pitch_info):
        '''
          Pitch Argument: Pitch String to use for direct lookup. Example: 'Fastball'
          Now this is where LOCATION is determined from pitch_strategy.py module.
          Heavily influenced by pitch effectiveness + batter's weaknesses
        '''
        batter_info = self.current_batter_obj()
        # 1. create batter weakness -> roster.py

        # If pitch matches weakness, boosts probability to put the pitch there
        # Example: 'High Fastball', pitcher most likely uses their fastball to the top of the zone

        #zone = self.strike_zone["INNER" if pitch.role == "catch_zone" else "OUTER"] # Is the pitch meant to land in the zone or out of the zone?
 
        print('PITCH PICK INTENT:', pitch)


        # control decides whether the intent lands in the zone
        
        # If roll ended up as 'Perfect' & 'Solid', then intended needs to match execution


       # return zone, label


    def pitch_to_zone(self, chosen_pitch, location_choice):
        """EXECUTION orchestrator.

        Receives the INTENT dict from pitch_location and resolves the pitch to
        its final executed result. Returns:
          {
            "pitch": str,                    # "Slider", ...
            "coordinate": (x, y),            # actual location on the grid
            "zone_label": str,               # "Top-Left", "Bottom-Right", ...
            "accuracy": str,                 # Perfect..Way Off
            "movement": str,                 # movement tier
            "effective": bool,               # did the pitch play as intended
            "velocity": float,               # thrown mph, sampled from the pitch's range
          }
        """
        # Intent vs Execution: the intent says where it SHOULD go; the
        # execution decides where it ACTUALLY goes.



        zone = self.strike_zone["INNER" if location_choice["location_result"] == 'in_zone' else "OUTER"]

        executed = self._resolve_coordinate(
            chosen_pitch, zone, location_choice["intended_label"], chosen_pitch.effectiveness,
            location_choice["dice"]["control"], location_choice["velocity_mph"])
        return executed


    def _label_to_coord(self, zone, label, batter_hand):
          """Relative label ("down_away", "up_in") -> (x, y) coordinate.
  
          Grid is the CATCHER'S POV (as shown on screen): (0,0)=Top-Left,
          (2,2)=Bottom-Right. An RHB stands on the third-base side (left of
          the screen): "in" is on the left, "away" on the right; mirrored
          for an LHB (first-base side, right of screen).
          """
          is_lhb = batter_hand.startswith("L")
          row = 0 if "up" in label else 2 if "down" in label else 1
          if "away" in label:
              col = 0 if is_lhb else 2
          elif "in" in label:
              col = 2 if is_lhb else 0
          else:
              col = 1
  
          coord = (row, col)
          # Clamp to the grid if that cell doesn't exist (e.g. OUTER corners).
          return coord if coord in zone else (row, 1)

    def _resolve_accuracy(self, zone, label, effectiveness, batter_hand, controlled):
        """Accuracy check: intended coord -> tier roll -> drift. Returns (coord, tier).
        A controlled pitch (control dice True) forces a 0-step tier (Perfect/Solid)
        so the pitch lands exactly on the intended cell.
        """
        def _accuracy_tier(control_rating):
          """Roll the accuracy tier (Perfect..Way Off), weighted by control."""
          print('CONTROL:', control_rating)
          roll = random.uniform(0, 100)
          odds = 40 + control_rating * 0.4   # Max +40% at a rating of 100
          if roll <= odds * 0.20:
              return "Perfect"
          if roll <= odds * 0.50:
              return "Solid"
          if roll <= odds * 0.80:
              return "Slightly off"
          if roll <= odds + 15:
              return "Inaccurate"
          return "Way Off"

        
        intended = self._label_to_coord(zone, label, batter_hand) # including batter's hand to have correct direction
        if controlled:
            tier = random.choice(["Perfect", "Solid"])  # both 0 steps in drift_map
        else:
            tier = _accuracy_tier(effectiveness["control"])  # Perfect..Way Off

        actual = self._apply_drift(intended, tier, zone)     
        print('RESOLVE ACCURACY: ',actual, tier)
         # shift, clamp to zone
        return actual, tier

    def _resolve_movement(self, pitch_type, effectiveness, velocity_mph):
        """Movement check: life/ride/spin quality. Returns (movement_tier, effective_bool)."""
        movement_rating = effectiveness["movement"]
        break_rating = effectiveness["break"]
        velocity_rating = velocity_mph  # sampled concrete mph for this pitch

        # Simple first pass: average the movement criteria into one quality roll.
        rating = (movement_rating + break_rating + velocity_rating) / 3
        roll = random.uniform(0, 100)
        if roll <= 40 + rating * 0.4:
            tier, effective = "Live", True
        elif roll <= 40 + rating * 0.4 + 20:
            tier, effective = "Flat", False
        else:
            tier, effective = "Dead", False
        return tier, effective

    def _resolve_velocity(self, pitch_type):
        dice = {}
        velocity = None

        for criterion, rating in pitch_type.effectiveness.items():
            if isinstance(rating, tuple):
                rating = random.uniform(rating[0], rating[1])  # concrete mph sample
                if criterion == "velocity":
                    velocity = round(rating, 1)
            threshold = 40 + rating * 0.4
            dice[criterion] = random.uniform(0, 100) <= threshold

        return velocity

    def _resolve_coordinate(self, chosen_pitch, zone, label, effectiveness, controlled, velocity_mph):
        """Combine accuracy + movement into the final executed result."""
        pitcher_hand = self.current_pitcher_obj().handedness
        batter_hand = self.current_batter().handedness

        coordinate, accuracy_tier = self._resolve_accuracy(
            zone, label, effectiveness, batter_hand, controlled)
        movement_tier, effective = self._resolve_movement(chosen_pitch.name, effectiveness, velocity_mph)



        return {
            "pitch": chosen_pitch.name,
            "coordinate": coordinate,
            "zone_label": zone.get(coordinate, "Unknown"),
            "accuracy": accuracy_tier,
            "movement": movement_tier,
            "effective": effective,
            "velocity": velocity_mph,
        }


    def _apply_drift(self, intended, tier, zone):
        """Shift the intended coordinate by the accuracy tier, clamped to the grid."""
        drift_map = {
            "Perfect": 0, "Solid": 0,
            "Slightly off": 1, "Inaccurate": 2,
            "Way Off": 3,
        }
        steps = drift_map[tier]
        row, col = intended
        print('STEPS', steps)
        print('INTENDED', row, col)
        for _ in range(steps):
            options = [(row + 1, col), (row - 1, col), (row, col + 1), (row, col - 1)]
            valid = [c for c in options if c in zone]
            if not valid:
                break
            row, col = random.choice(valid)

            
        return (row, col)

        # resolves final pitch -> coming to the plate to be RETURNED    
        # RETURNS final coordinate, chosen_pitch, Location Tier String, Movement Tier string
        # Will be given -> displayPitch() function
  
    def pitch(self):
        """Simulate a pitch, update game state, return (result_string, (outs, balls, strikes))."""
        """ STATCAST DATASETS (OVERALL):
            Balls: 35.9%
            Called Strikes: 17.1%
            Swinging Strikes: 9.9%
            Foul Balls: 17.9%
            Hit Into Play (Contact): 18.2% 

            80.8% Strike/Ball
            18.2% for Contact  
        """
        if self.game_over:
            return "Game already over. Reset to play again.", (self.outs, self.balls, self.strikes)
        

        pitcher = self.current_pitcher_obj()# Pitcher object
        pitch_strategy = self.pitch_choice()   # Strategy -> Returns pitch string -> For Pitch intent (LOCATION, movement)
       # print('CHOSEN PITCH:', pitch_strategy)  # Pitch instance w/ effectiveness
        pitch_intent = self.pitch_intent_manager(pitch_strategy, pitcher.arsenal[pitch_strategy])                  # intent + dice rolls
        # Above happens before the pitch is THROWN
       # pitch_to_zone = self.pitch_to_zone(pitch, location_choice)
        # pitch_to_zone is the intent vs. execution, what pitcher wants vs. what REALLY happens

        outcome = self.resolve_pitch_outcome()

        s = self._last_strategy
      #  print(f"Strategy: {s['leverage']} {s['weights']} -> {s['category']}")
       # print(f"Intent: {location_choice['intended_label']} -> {location_choice['location_result']} {location_choice['dice']}") # source of issue
        # OUTPUT EXAMPLE: Intent: up_in -> in_zone {'control': True, 'movement': False, 'break': True, 'velocity': True}
      #  print('PITCH TO ZONE', pitch_to_zone) # ---> display_pitch(), animation
        # OUTPUT EXAMPLE: Needs in or out_of_zone
        #  {'pitch': 'Cutter', 'coordinate': (0, 1), 'zone_label': ('INNER', 'Top-Middle'), 'accuracy': 'Inaccurate', 
        #  'movement': 'Live', 'effective': True} -> if in-accurate, move coordinate


        # outcome = self.resolve_pitch_outcome(...)  ← commented out


        # outcome is ALWAYS ''
        ''' Takes in pitch type, pitch rating and location result -> returns 
            - Pitch Location
            - Pitch Accuracy
            - Pitch Movement -> resolve_pitch_outcome
        '''
        # Above takes place before the batter reacts

        # resolve_pitch_outcome

        # IF execution is solid or above, it should always match with what was intented
        
        return outcome, (self.outs, self.balls, self.strikes)


    def resolve_pitch_outcome(self):
        # This function takes is the FINAL RESULT of the pitch, combining & returning Pitcher's & Batter's Results in a weighted randomizer
        ''' INPUT:
            - Pitch Location
            - Pitch Accuracy
            - Pitch Movement
            - Batter's Ratings (EVENTUALLY)
            - Batter's Tendencies (EVENTUALLY)
            - Hot/Cold (EVENTUALLY)
        '''

        # pitch() -> begins process

        # Batter receives boost if pitch() was unintended

        roll = random.uniform(0, 100)
           

        # In-play or not
        if roll < 0.450:   # 45% strike ~44.9% according to Statcast
            self.strikes += 1
            result = "Strike!"
            if self.strikes >= 3:
                result = "Strikeout! Batter is out."
                self._handle_out()
        elif roll < 0.700: # 35% ball ~35.9% according to Statcast
            self.balls += 1
            result = "Ball!"
            if self.balls >= 4:
                result = "Walk!"
                self._handle_walk()
        else:      # 20% contact (hit, foul, out) ~18.2% according to Statcast
            # Need to incorporate fouls
            # in_play_resolution function
            if random.random() > 0.700:
                # Hit – determine type from pitch -> batter ratings
                hit_roll = random.random()
                if hit_roll < 0.6:    # 60% of hits = single
                    result = "Single!"
                    runs = self._place_batter_on_base(1)
                elif hit_roll < 0.85: # 25% double
                    result = "Double!"
                    runs = self._place_batter_on_base(2)
                elif hit_roll < 0.95: # 10% triple
                    result = "Triple!"
                    runs = self._place_batter_on_base(3)
                else:                 # 5% home run
                    result = "HOME RUN!"
                    runs = self._place_batter_on_base(4)
                
                if runs > 0:
                    if self.top_bottom == "top":
                        self.score[self.away_name] += runs
                    else:
                        self.score[self.home_name] += runs
                    result += f" {runs} run(s) score!"
                
                self._reset_count()
                self.advance_batter()
            else:
                # Out in play
                result = "Out!"
                self._handle_out()
        return result

    def _handle_walk(self):
        """Walk: batter goes to 1st, runners advance if forced."""
        runs = 0
        # If bases loaded, runner on 3rd scores on walk
        if self.bases[1] and self.bases[2] and self.bases[3]:
            runs += 1
            # Move runner from 3rd to home, others shift
            self.bases[3] = False
            # 2nd to 3rd, 1st to 2nd
            self.bases[3] = self.bases[2]
            self.bases[2] = self.bases[1]
            self.bases[1] = True
        else:
            # Find first empty base from 1st up, shift runners forward
            if not self.bases[1]:
                self.bases[1] = True
            elif not self.bases[2]:
                self.bases[2] = True
            elif not self.bases[3]:
                self.bases[3] = True
            else:
                # Loaded – already handled above
                pass
        if runs > 0:
            if self.top_bottom == "top":
                self.score[self.away_name] += runs
            else:
                self.score[self.home_name] += runs
        self._reset_count()
        self.advance_batter()

    def _handle_out(self):
        """Out: increment outs, optionally advance runners on sacrifice (simplified: no advance)."""
        self.outs += 1
        self._reset_count()
        # In a fuller simulation, some outs (sacrifice flies) could advance runners.
        # For simplicity, we do not advance runners on outs.
        self.advance_batter()
        # If 3 outs, inning ends
        if self.outs >= 3:
            self._end_inning()

    def _end_inning(self):
        self.outs = 0
        self._reset_count()
        self._clear_bases()
        if self.top_bottom == "top":
            self.top_bottom = "bottom"
        else:
            self.top_bottom = "top"
            self.inning += 1
        if self.inning > 9:
            self.game_over = True

    def get_game_state_text(self):

        """Return formatted string of current game state."""
        lines = []
        lines.append(f"Inning: {self.inning} ({self.top_bottom.upper()})")
        lines.append(f"Score: {self.away_name} {self.score[self.away_name]} - {self.home_name} {self.score[self.home_name]}")
        lines.append(f"Outs: {self.outs}   Balls: {self.balls}   Strikes: {self.strikes}")
        
        # Display bases
        base_str = ""
        base_str += "1B: " + ("X" if self.bases[1] else "_") + "  "
        base_str += "2B: " + ("X" if self.bases[2] else "_") + "  "
        base_str += "3B: " + ("X" if self.bases[3] else "_")
        lines.append(f"Bases: {base_str}")
        
        batter = self.current_batter_obj()
        pitcher = self.current_pitcher_obj()
        lines.append(f"Batter: {batter.name} ({batter.position})")
        lines.append(f"Pitcher: {pitcher.name} ({pitcher.position})")
        
        if self.game_over:
            winner = self.away_name if self.score[self.away_name] > self.score[self.home_name] else self.home_name
            lines.append(f"GAME OVER - {winner} wins!")
        return "\n".join(lines)
    
if __name__ == "__main__":
    import os, sys, random
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    try:
        from backend.engine.roster import rosters # I think this where I receive Judge & Mclean
    except ImportError:
        from backend.engine.roster import rosters

    random.seed(4)  # reproducible debugging with the same pitch/hit sequence over and over again

    away = rosters["away_team"]
    home = rosters["home_team"]
    game = GameEngine(home, away, "Home", "Away")

    print(game.get_game_state_text())
    for i in range(1):          # cap so a full 9-inning game doesn't run forever - 2 full top-bottom innings
        result, _ = game.pitch()
        print(f"[{i:>2}] {result}")
        if game.game_over:
            break
    print(game.get_game_state_text())