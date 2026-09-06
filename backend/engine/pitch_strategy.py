# pitch_strategy.py
import random
# Statcast fastball-family classification: Cutter counts as a fastball.
PITCH_CATEGORIES = {
    "4-Seam Fastball": "Fastball",
    "Cutter": "Fastball",
    "Slider": "Breaking",
    "Sweeper": "Breaking",
    "Curveball": "Breaking",
    "Slow Curve": "Breaking",
    "Changeup": "OffSpeed",
    "Sinker": "OffSpeed"
}

# Needs to take in pitcher's hot/cold zones (from roster.py) -> adjust strategy
# pitch_strategy.py

BASE_MATRIX = {
    "NEUTRAL":    {"Fastball": 0.55, "Breaking": 0.30, "OffSpeed": 0.15},
    "AHEAD":      {"Fastball": 0.25, "Breaking": 0.55, "OffSpeed": 0.20},
    "BEHIND":     {"Fastball": 0.75, "Breaking": 0.15, "OffSpeed": 0.10},
    "FULL_COUNT": {"Fastball": 0.60, "Breaking": 0.25, "OffSpeed": 0.15}
}

# backend/engine/pitch_strategy.py

class PitchStrategy:
    # 1. INITIALIZATION FOR THE CURRENT PITCHER AT THE TOP 
    def __init__(self, pitcher, batter):
        self.pitcher = pitcher
        self.pitch_arsenal = getattr(pitcher, 'pitch_arsenal', [])
        self.pitch_ratings = getattr(pitcher, 'ratings', [])
        self.batter = batter # Batter Object


    # 2. HELPER FUNCTIONS IN THE MIDDLE
    def get_leverage_state(self, balls, strikes):
        if balls == 3 and strikes == 2:
            return "FULL_COUNT"
        elif strikes > balls:
            return "AHEAD"
        elif balls > strikes:
            return "BEHIND"
        return "NEUTRAL"

    def filter_pitch_info(self, batter_handedness="rhb", arsenal=None):
        '''This function pulls out the specific pitch info we need from self.pitch_arsenal:
           1. 'pitch'
           2. 'usage_pct_vs_(rhb or lhb)'
           3. 'avg_velo_mph'
           4. 'max_velo_mph
        '''
        if arsenal is None:
           arsenal = self.pitch_arsenal

        pitch_array = [] # Using a list because I'm not going to modify any of the attributes
                         # I'm only going to read-only -> to randomize
        
        if batter_handedness == 'L': 
            batter_handedness = "lhb"
        else: 
            batter_handedness = "rhb"

        usage_side = f"usage_pct_vs_{batter_handedness}"
                        
        for i, pitch_info in enumerate(arsenal):
            pitch_obj = {
                'pitch': pitch_info['pitch'],
                usage_side: pitch_info[usage_side],
                'avg_velocity': pitch_info['avg_velo_mph'],
                'max_velocity': pitch_info['max_velo_mph']
            }

            pitch_array.append(pitch_obj)
             

          #  info_hash[i] = pitch_obj
       # print('INSIDE FILTER FUNCTION:', batter_handedness)
        return pitch_array

    def pitch_usage_weights(self, usage_rates):
        # Usage adjusting the probabilities 
        '''Takes in Pitcher's usage rates of each pitch = in the form of a object hash'''
        pass

    # 3. MAIN WORKHORSE RETURNED TO GAME ENGINE AT THE BOTTOM
    def choose_pitch(self, balls, strikes, double_play_situation=False):
        leverage = self.get_leverage_state(balls, strikes)
       # probs = dict(BASE_MATRIX[leverage])

        arsenal = self.pitch_arsenal
        # Access self.pitcher directly here!
        pitch_info = self.filter_pitch_info(self.batter.handedness)
        print('PITCHINFO:', pitch_info)

       # Need to return full probability for each count with Batter's report adjusting chances -> GameEngine's randomizer 


       # return leverage, probs