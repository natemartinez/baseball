# pitch_strategy.py
import random
# Statcast fastball-family classification: Cutter counts as a fastball.
PITCH_CATEGORIES = {
    "Fastball": "Fastball",
    "Cutter": "Fastball",
    "Slider": "Breaking",
    "Curveball": "Breaking",
    "Changeup": "OffSpeed",
}

# Needs to take in pitcher's hot/cold zones (from roster.py) -> adjust strategy

class PitchStrategyMVP:
    def __init__(self):
        # Step 1 & 3: Define baseline probabilities based on leverage states

        # WEIGHTS ARE STORED HERE
        self.base_matrix = {
            "NEUTRAL":    {"Fastball": 0.55, "Breaking": 0.30, "OffSpeed": 0.15},
            "AHEAD":      {"Fastball": 0.25, "Breaking": 0.55, "OffSpeed": 0.20},
            "BEHIND":     {"Fastball": 0.75, "Breaking": 0.15, "OffSpeed": 0.10},
            "FULL_COUNT": {"Fastball": 0.60, "Breaking": 0.25, "OffSpeed": 0.15}
        }

    def get_leverage_state(self, balls, strikes):
        """Step 2: Map the 12 possible counts to 4 leverage states"""
        if balls == 3 and strikes == 2:
            return "FULL_COUNT"
        elif strikes > balls:
            return "AHEAD"
        elif balls > strikes:
            return "BEHIND"
        else:
            return "NEUTRAL"

    def calculate_probabilities(self, balls, strikes, double_play_situation=False):
        leverage = self.get_leverage_state(balls, strikes)
        # Copy the baseline weights for the specific leverage state
        probs = dict(self.base_matrix[leverage])

        # Step 4: Apply situation modifier (Double Play Context)
        if double_play_situation and leverage in ["NEUTRAL", "AHEAD"]:
            probs["Fastball"] += 0.15
            probs["OffSpeed"] += 0.10
            probs["Breaking"] -= 0.25

            # Prevent negative numbers
            probs["Breaking"] = max(0.0, probs["Breaking"])

            # Re-normalize weights to equal exactly 1.0
            total = sum(probs.values())
            for key in probs:
                probs[key] = round(probs[key] / total, 3)

        return leverage, probs

    def select_pitch(self, probs):
        pitches = list(probs.keys())
        weights = list(probs.values())
        return random.choices(pitches, weights=weights, k=1)[0]



