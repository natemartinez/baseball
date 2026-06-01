# game_engine.py
import random

class GameEngine:
    def __init__(self, home_roster, away_roster, home_name, away_name):
        self.home_roster = home_roster
        self.away_roster = away_roster
        self.home_name = home_name
        self.away_name = away_name

        # Game state
        self.inning = 1
        self.outs = 0
        self.top_bottom = "top"  # top = away bats, bottom = home bats
        self.score = {self.away_name: 0, self.home_name: 0}

        # Bases: 0=empty, 1=runner on 1st, 2=2nd, 3=3rd, 4=1st&2nd, 5=1st&3rd, 6=2nd&3rd, 7=loaded
        # Using a simple dict for clarity
        self.bases = {1: False, 2: False, 3: False}

        # Batting order
        self.away_lineup = away_roster['position_players'][:]
        self.home_lineup = home_roster['position_players'][:]
        self.current_batter_index = 0

        self.balls = 0
        self.strikes = 0
        self.game_over = False

        # Starting pitchers
        self.away_pitcher = away_roster['pitchers']['starters'][0]
        self.home_pitcher = home_roster['pitchers']['starters'][0]

    def current_batter(self):
        if self.top_bottom == "top":
            return self.away_lineup[self.current_batter_index]
        else:
            return self.home_lineup[self.current_batter_index]

    def current_pitcher_obj(self):
        if self.top_bottom == "top":
            return self.home_pitcher
        else:
            return self.away_pitcher

    def advance_batter(self):
        self.current_batter_index = (self.current_batter_index + 1) % 9

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

    def pitch(self):
        """Simulate a pitch, update game state, return (result_string, (outs, balls, strikes))."""
        if self.game_over:
            return "Game already over. Reset to play again.", (self.outs, self.balls, self.strikes)

        # Random outcome with enhanced probabilities
        roll = random.random()
        
        # Strike, ball, or in-play
        if roll < 0.35:   # 35% strike
            self.strikes += 1
            result = "Strike!"
            if self.strikes >= 3:
                result = "Strikeout! Batter is out."
                self._handle_out()
        elif roll < 0.60: # 25% ball
            self.balls += 1
            result = "Ball!"
            if self.balls >= 4:
                result = "Walk!"
                self._handle_walk()
        else:             # 40% ball in play (hit or out)
            # In-play outcomes: 60% hit, 40% out
            if random.random() < 0.6:
                # Hit – determine type
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
        
        # After any out, check if inning ends
        if self.outs >= 3:
            self._end_inning()
        
        return result, (self.outs, self.balls, self.strikes)

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
        # If 3 outs, inning ends (handled in pitch)

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
        
        batter = self.current_batter()
        pitcher = self.current_pitcher_obj()
        lines.append(f"Batter: {batter.name} ({batter.position})")
        lines.append(f"Pitcher: {pitcher.name} ({pitcher.position})")
        
        if self.game_over:
            winner = self.away_name if self.score[self.away_name] > self.score[self.home_name] else self.home_name
            lines.append(f"GAME OVER - {winner} wins!")
        return "\n".join(lines)