from dataclasses import dataclass
from enum import Enum
import math
import random
from typing import Any, Dict, Optional, Tuple


class TimingTier(str, Enum):
    PERFECT = "PERFECT"
    GOOD = "GOOD"
    OKAY = "OKAY"
    POOR = "POOR"


class AbilityTier(str, Enum):
    ELITE = "ELITE"
    GREAT = "GREAT"
    GOOD = "GOOD"
    OKAY = "OKAY"
    MEDIOCRE = "MEDIOCRE"
    POOR = "POOR"


@dataclass
class PitchCommandConfig:
    command_rating: float  # 0 to 100 scale
    pitch_type_mod: float = 1.0  # 4SFB = 1.0, Slider = 1.15, Knuckleball = 1.35
    stamina_penalty: float = 0.0  # 0.0 (fresh) to 0.40 (fatigued)
    composure_penalty: float = 0.0  # 0.0 (calm) to 0.40 (shaky)
    consistency_modifier: float = 1.0  # 1.0 (perfect) to 2.0 (wild)


TIMING_MULTIPLIERS: Dict[TimingTier, float] = {
    TimingTier.PERFECT: 0.52,
    TimingTier.GOOD: 1.00,
    TimingTier.OKAY: 1.97,
    TimingTier.POOR: 3.75,
}


def _normalize_dict_key(key: Any) -> str:
    k = key.value if hasattr(key, "value") else str(key)
    return k.strip().upper()


class TimingDict(dict):
    """Dictionary subclass that transparently maps TimingTier enum keys and strings,
    while iterating over exactly the 4 timing tier values."""
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.update(*args, **kwargs)

    def __getitem__(self, key):
        return super().__getitem__(_normalize_dict_key(key))

    def __setitem__(self, key, value):
        super().__setitem__(_normalize_dict_key(key), value)

    def __delitem__(self, key):
        super().__delitem__(_normalize_dict_key(key))

    def get(self, key, default=None):
        return super().get(_normalize_dict_key(key), default)

    def __contains__(self, key):
        return super().__contains__(_normalize_dict_key(key))

    def setdefault(self, key, default=None):
        return super().setdefault(_normalize_dict_key(key), default)

    def pop(self, key, *args):
        return super().pop(_normalize_dict_key(key), *args)

    def update(self, *args, **kwargs):
        if args:
            other = args[0]
            if hasattr(other, "items"):
                for k, v in other.items():
                    self[_normalize_dict_key(k)] = v
            else:
                for k, v in other:
                    self[_normalize_dict_key(k)] = v
        for k, v in kwargs.items():
            self[_normalize_dict_key(k)] = v


class AbilityDict(dict):
    """Dictionary subclass that transparently maps AbilityTier enum keys and strings,
    while iterating over exactly the 6 ability tier entries."""
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.update(*args, **kwargs)

    def __getitem__(self, key):
        return super().__getitem__(_normalize_dict_key(key))

    def __setitem__(self, key, value):
        super().__setitem__(_normalize_dict_key(key), value)

    def __delitem__(self, key):
        super().__delitem__(_normalize_dict_key(key))

    def get(self, key, default=None):
        return super().get(_normalize_dict_key(key), default)

    def __contains__(self, key):
        return super().__contains__(_normalize_dict_key(key))

    def setdefault(self, key, default=None):
        return super().setdefault(_normalize_dict_key(key), default)

    def pop(self, key, *args):
        return super().pop(_normalize_dict_key(key), *args)

    def update(self, *args, **kwargs):
        if args:
            other = args[0]
            if hasattr(other, "items"):
                for k, v in other.items():
                    self[_normalize_dict_key(k)] = v
            else:
                for k, v in other:
                    self[_normalize_dict_key(k)] = v
        for k, v in kwargs.items():
            self[_normalize_dict_key(k)] = v


BASELINE_TIMING_PROBABILITIES: Dict[Any, Dict[Any, float]] = AbilityDict({
    AbilityTier.ELITE.value: TimingDict({
        TimingTier.PERFECT.value: 0.45,
        TimingTier.GOOD.value: 0.45,
        TimingTier.OKAY.value: 0.08,
        TimingTier.POOR.value: 0.02,
    }),
    AbilityTier.GREAT.value: TimingDict({
        TimingTier.PERFECT.value: 0.35,
        TimingTier.GOOD.value: 0.48,
        TimingTier.OKAY.value: 0.14,
        TimingTier.POOR.value: 0.03,
    }),
    AbilityTier.GOOD.value: TimingDict({
        TimingTier.PERFECT.value: 0.25,
        TimingTier.GOOD.value: 0.50,
        TimingTier.OKAY.value: 0.20,
        TimingTier.POOR.value: 0.05,
    }),
    AbilityTier.OKAY.value: TimingDict({
        TimingTier.PERFECT.value: 0.15,
        TimingTier.GOOD.value: 0.45,
        TimingTier.OKAY.value: 0.30,
        TimingTier.POOR.value: 0.10,
    }),
    AbilityTier.MEDIOCRE.value: TimingDict({
        TimingTier.PERFECT.value: 0.08,
        TimingTier.GOOD.value: 0.37,
        TimingTier.OKAY.value: 0.37,
        TimingTier.POOR.value: 0.18,
    }),
    AbilityTier.POOR.value: TimingDict({
        TimingTier.PERFECT.value: 0.05,
        TimingTier.GOOD.value: 0.30,
        TimingTier.OKAY.value: 0.40,
        TimingTier.POOR.value: 0.25,
    }),
})

PITCH_TYPE_MODIFIERS: Dict[str, float] = {
    "4SFB": 1.00,
    "2SFB": 1.02,
    "CUT": 1.05,
    "SNK": 1.05,
    "CH": 1.08,
    "SL": 1.15,
    "SWP": 1.18,
    "CB": 1.20,
    "SPL": 1.25,
    "KN": 1.35,
}

PITCH_TYPE_ALIASES: Dict[str, str] = {
    "FOUR-SEAM FASTBALL": "4SFB",
    "4-SEAM FASTBALL": "4SFB",
    "TWO-SEAM FASTBALL": "2SFB",
    "2-SEAM FASTBALL": "2SFB",
    "CUTTER": "CUT",
    "SINKER": "SNK",
    "POWER SINKER": "SNK",
    "SI": "SNK",
    "CHANGEUP": "CH",
    "CIRCLE CHANGEUP": "CH",
    "SLIDER": "SL",
    "SWEEPER": "SWP",
    "SPIN MONSTER SWEEPER": "SWP",
    "CURVEBALL": "CB",
    "SPIKE CURVEBALL": "CB",
    "SLOW CURVE": "CB",
    "KNUCKLE CURVE": "CB",
    "KC": "CB",
    "SPLITTER": "SPL",
    "FORKBALL": "SPL",
    "GHOST FORK": "SPL",
    "GFORK": "SPL",
    "FS": "SPL",
    "KNUCKLEBALL": "KN",
}


def get_ability_tier(effective_command: float) -> AbilityTier:
    """Returns AbilityTier based on effective command rating:

    - ELITE: >= 90.0
    - GREAT: 80.0 to 89.99
    - GOOD: 70.0 to 79.99
    - OKAY: 60.0 to 69.99
    - MEDIOCRE: 50.0 to 59.99
    - POOR: < 50.0
    """
    cmd = float(effective_command)
    if cmd >= 90.0:
        return AbilityTier.ELITE
    elif cmd >= 80.0:
        return AbilityTier.GREAT
    elif cmd >= 70.0:
        return AbilityTier.GOOD
    elif cmd >= 60.0:
        return AbilityTier.OKAY
    elif cmd >= 50.0:
        return AbilityTier.MEDIOCRE
    else:
        return AbilityTier.POOR


def get_pitch_type_modifier(pitch_type: str) -> float:
    """Returns difficulty multiplier for a pitch type or pitch ID. Defaults to 1.00."""
    if not pitch_type:
        return 1.00
    cleaned = str(pitch_type).strip().upper()
    if cleaned in PITCH_TYPE_MODIFIERS:
        return PITCH_TYPE_MODIFIERS[cleaned]
    mapped = PITCH_TYPE_ALIASES.get(cleaned)
    if mapped and mapped in PITCH_TYPE_MODIFIERS:
        return PITCH_TYPE_MODIFIERS[mapped]
    return 1.00



def calculate_execution_radius_inches(
    tier: TimingTier,
    config: PitchCommandConfig,
) -> float:
    """Calculates the execution error circle radius (in inches) at the front

    edge of home plate based on command rating, pitch type, stamina, and
    release timing.
    """
    r_max = 3.60  # Maximum radius at 0 Command (inches)
    r_min = 0.90  # Minimum radius at 100 Command (inches)

    # 1. Base Perfect Radius
    clamped_rating = max(0.0, min(100.0, config.command_rating))
    base_perfect = r_max - (clamped_rating / 100.0) * (r_max - r_min)

    # 2. Scale by Timing Tier and Modifiers
    timing_scalar = TIMING_MULTIPLIERS[tier]
    final_radius = (
        base_perfect
        * timing_scalar
        * config.pitch_type_mod
        * (1.0 + config.stamina_penalty)
    )

    return round(final_radius, 2)


def sample_plate_offset(
    radius_inches: float,
    tier: TimingTier,
) -> Tuple[float, float]:
    """Generates an (X, Z) offset in inches from the intended pitch target.

    - PERFECT clusters tightly near the center of the reticle.
    - OKAY and POOR bias outward toward the edge.
    """
    angle = random.uniform(0.0, 2.0 * math.pi)

    if tier == TimingTier.PERFECT:
        # Concentrated Gaussian distribution around target center
        normalized_r = min(1.0, abs(random.gauss(0.0, 0.35)))
    elif tier == TimingTier.GOOD:
        normalized_r = math.sqrt(random.uniform(0.0, 1.0))
    else:
        # Outer-ring bias for mistimed releases
        normalized_r = random.uniform(0.50, 1.0)

    distance = normalized_r * radius_inches
    dx = distance * math.cos(angle)
    dz = distance * math.sin(angle)

    return round(dx, 2), round(dz, 2)


# --- Example Usage ---
if __name__ == "__main__":
    pitch_config = PitchCommandConfig(
        command_rating=80.0,
        pitch_type_mod=1.0,  # 4SFB
        stamina_penalty=0.0,  # Fresh arm
    )

    for timing in TimingTier:
        r = calculate_execution_radius_inches(timing, pitch_config)
        offset_x, offset_z = sample_plate_offset(r, timing)
        print(
            f"[{timing.value:<19}] "
            f"Radius: {r:>5.2f} in | "
            f"Sample Miss (ΔX, ΔZ): ({offset_x:>+5.2f}\", {offset_z:>+5.2f}\")"
        )