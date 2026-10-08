# Deterministic Pitching Logic & Simulation Rules

> **Document Status**: Live & Interactive Engine Synced  
> **Target File**: `/pitching_logic.md` (Project Root)  
> **Engine Version**: MLB Statcast Deterministic v4.8  
> **Last Synchronized**: 2026-09-12T15:10:00Z  
> **Active Pitcher**: Gerrit Cole (NYY) | **Active Batter**: Aaron Judge (NYY)

---

## 1. High-Level Architecture & Mathematical Pipeline

The baseball pitching engine simulates pitch sequences through a 5-stage deterministic pipeline. Rather than rolling arbitrary random numbers, every pitch selection, trajectory, and plate outcome is derived from real-world **Statcast aerodynamics**, **pitcher command variance**, **count pressure**, and **batter-specific hot-zone vulnerabilities**.

```
+-----------------------------------------------------------------------------------+
|                            5-STAGE PITCH SIMULATION PIPELINE                      |
+-----------------------------------------------------------------------------------+
|  [Stage 1: State Evaluation]                                                      |
|  Vector S = (Balls, Strikes, Outs, Runners [1B, 2B, 3B], Leverage Index)         |
|                                |                                                  |
|  [Stage 2: Deterministic Weight Modulation]                                       |
|  w_pitch = w_base * M_count * M_situation * M_stuff                               |
|  w_zone  = w_base * M_batter_hotzones * M_count * M_situation                     |
|                                |                                                  |
|  [Stage 3: Aerodynamic Trajectory Generation]                                     |
|  v0 ~ Uniform(minV, maxV) | Spin ~ Uniform(minSpin, maxSpin)                      |
|  Break = f(Magnus Force, Spin Axis, Seam Orientation)                             |
|                                |                                                  |
|  [Stage 4: 13-Zone Command Variance & Plate Arrival]                              |
|  r_arrival = r_target + GaussianJitter(Control Rating)                            |
|                                |                                                  |
|  [Stage 5: Batter Decision & Collision Resolution]                               |
|  P(Swing) = f(Zone, Pitch, Count)                                                |
|  Outcome  = CollisionMatrix(Bat Speed, Pitch Velocity, Hot Zone Slugging)        |
+-----------------------------------------------------------------------------------+
```

---

## 2. Active Simulation Rules Configuration

The live pitching engine reads the following configuration matrix directly from this document. When this document is updated via the web interface or API, the active simulation weights immediately adapt:

```json:rules_config
{
  "version": "1.3.0",
  "last_modified": "2026-09-12T23:59:50.511Z",
  "count_adjustments": {
    "ahead_two_strikes": {
      "sweeper_weight_mult": 3,
      "curveball_weight_mult": 2,
      "fastball_weight_mult": 0.55,
      "chase_zone_mult": 3.4,
      "heart_zone_mult": 0.12
    },
    "behind_hitters_count": {
      "fastball_weight_mult": 2.6,
      "sinker_weight_mult": 1.9,
      "sweeper_weight_mult": 0.35,
      "chase_zone_mult": 0.12,
      "strike_zone_mult": 2
    }
  },
  "batter_hot_zones": {
    "batter_name": "Aaron Judge",
    "hot_zone_neutral_penalty_mult": 0.22,
    "hot_zone_behind_penalty_mult": 0.7,
    "cold_zone_target_bonus_mult": 2.4,
    "slugging_threshold_hot": 0.5,
    "slugging_threshold_cold": 0.28
  },
  "batter_aggressiveness": {
    "first_pitch_heart_swing_mult": 0.55,
    "first_pitch_take_all_the_way_prob": 0.05,
    "three_oh_take_mult": 0.12,
    "two_strike_expansion_mult": 1.65,
    "hitters_count_ambush_mult": 1.25,
    "chase_discipline_mult": 0.65
  },
  "pa_hidden_value": {
    "league_avg_pitches_per_pa": 3.9,
    "fatigue_coefficient": 0.0042,
    "high_pitch_threshold": 75,
    "fatigue_multiplier": 1.45,
    "bullpen_acceleration_scaling": 1000,
    "deep_pa_threshold": 6,
    "tactical_intel_coefficient": 0.015
  },
  "game_situations": {
    "double_play": {
      "sinker_weight_mult": 2.8,
      "curveball_weight_mult": 1.3,
      "fastball_weight_mult": 0.45,
      "lower_strike_zones_mult": 3,
      "chase_low_mult": 2.6,
      "upper_zones_mult": 0.3
    },
    "bases_loaded": {
      "ahead_sweeper_mult": 2.5,
      "behind_fastball_mult": 2.2,
      "chase_suppression_mult": 0.25
    },
    "scoring_position": {
      "high_contact_suppression_mult": 0.4,
      "cold_zone_attack_mult": 2.2
    }
  },
  "statcast_bonuses": {
    "stuff_plus_threshold": 125,
    "stuff_plus_bonus_mult": 1.15,
    "whiff_rate_ahead_bonus_mult": 1.25,
    "ground_ball_dp_bonus_mult": 1.35
  }
}
```

---

## 3. Count Weight Adjustments & Tactical Intent

The pitcher's strategic objective shifts dramatically depending on the count state $(b, s)$:

| Count State | Strategic Regime | Primary Weapon | Secondary Weapon | Pitch Weight Shifts | Zone Multiplier Shifts | Tactical Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **0-0 (First Pitch)** | `ESTABLISH_COUNT` | Four-Seam Fastball | Power Sinker | Fastball 1.2x, Sinker 1.1x | Shadow Zones 1.5x, Heart 0.4x | Gain count leverage without presenting middle-middle damage pitches. |
| **0-1, 1-1 (Even)** | `NEUTRAL_MIX` | Spin Sweeper | Four-Seam Fastball | Sweeper 1.3x, Fastball 1.0x | Low-Away 1.8x, Mid-In 1.2x | Keep hitter off-balance; mix high velocity with lateral sweep. |
| **0-2, 1-2 (Ahead)** | `TWO_STRIKE_PUT_AWAY` | Spin Monster Sweeper | Spike Curveball | Sweeper **3.0x**, Curve **2.0x**, Fastball **0.55x** | Chase Zones **3.4x**, Heart **0.12x** | Expand the strike zone into chase corridors. Whiff percentage is paramount (44.5% Whiff on Sweeper). |
| **2-0, 3-0, 3-1 (Behind)** | `CRITICAL_ZONE_CHALLENGE` | Four-Seam Fastball | Power Sinker | Fastball **2.6x**, Sinker **1.9x**, Sweeper **0.35x** | Inner Zones **2.0x**, Chase **0.12x** | Avoid free passes. Must challenge the zone with high-velocity heat while painting edges. |
| **3-2 (Full Count)** | `HIGH_LEVERAGE_BATTLE` | Four-Seam Fastball | Spin Monster Sweeper | Fastball 1.8x, Sweeper 1.5x | Lower-Away 2.2x, Upper-In 1.6x | Maximum pressure. Balancing swing-and-miss stuff against the penalty of Ball 4. |

---

## 4. Batter Hot-Zone Profile (Aaron Judge Slugging Map)

To avoid giving up home runs, the pitching engine evaluates the batter's slugging percentage ($SLG$) across all **13 designated plate coordinates**:

```
           [ CHASE HIGH (0.180 SLG) ]
  +-----------------------------------------+
  |  Upper-In (.650)  | Up-Mid (.510) | Up-Away (.350)  |
  |  -----------------+---------------+---------------  |
[C]  Mid-In (.540)    | HEART (.820)  | Mid-Away (.280) [C]
[I]  -----------------+---------------+--------------- [A]
[N]  Lower-In (.380)  | Low-Mid (.420)| Low-Away (.240) [W]
  +-----------------------------------------+
           [ CHASE LOW (0.150 SLG) ]
```

### Deterministic Defensive Adjustments:
1. **Heart Zone Penalty**:
   $$\text{Weight}_{\text{HEART}} = \text{BaseWeight} \times 0.22 \quad (\text{Neutral Count})$$
   $$\text{Weight}_{\text{HEART}} = \text{BaseWeight} \times 0.12 \quad (\text{0-2, 1-2 Count})$$
   $$\text{Weight}_{\text{HEART}} = \text{BaseWeight} \times 0.70 \quad (\text{3-0, 3-1 Count - Forced Strike})$$
2. **Cold Zone Exploitation**:
   - `lower-away` (0.240 SLG) and `middle-away` (0.280 SLG) receive an automatic **2.4x weighting multiplier**.
   - Sweepers breaking away from right-handed batters (16-19" of horizontal break) terminate naturally in the `lower-away` and `chase-away` corridors.

---

## 5. Game Situations & Leverage Adjustments

### A. Double Play Grounder Hunt (Runner on 1st, $< 2$ Outs)
- **Primary Goal**: Roll a 6-4-3 or 4-6-3 double play via high ground-ball rate contact.
- **Weapon of Choice**: **Power Sinker** (64.5% Ground Ball rate, 96.5 MPH, 18" run).
- **Weight Adjustments**:
  - `Power Sinker` Weight Multiplier: **2.8x**
  - `Spike Curveball` Weight Multiplier: **1.3x**
  - `Four-Seam Fastball` Weight Multiplier: **0.45x** (suppress elevated fly-balls)
- **Zone Targeting**:
  - `lower-in`, `lower-middle`, `lower-away`: **3.0x**
  - `chase-low`: **2.6x**
  - `upper-*` and `chase-high`: **0.30x**

### B. Bases Loaded Pressure
- **Ahead in Count (0-2, 1-2)**:
  - Strikeout is mandatory to prevent sacrifice flies or run-scoring grounders.
  - `Spin Monster Sweeper` multiplier: **2.5x**.
- **Behind in Count (3-0, 3-1)**:
  - Ball 4 forces home an unearned/earned run.
  - Chase zone multiplier suppressed to **0.25x**.
  - `Four-Seam Fastball` / `Power Sinker` multiplier: **2.2x**.

### C. Runner in Scoring Position (RISP)
- Elevating pitches is strictly penalized.
- High contact suppression multiplier: **0.40x** for upper zones.
- Cold-zone attacks focused on pitcher's glove-side edge.

---

## 6. Command Variance & Plate Arrival Math

Pitchers do not hit their exact target on every delivery. The final arrival coordinate $\vec{r}_{\text{actual}} = (x, y)$ in feet at the front of home plate is modeled using Gaussian command dispersion:

$$\Delta x = \mathcal{N}\left(0, \sigma^2\right), \quad \Delta y = \mathcal{N}\left(0, \sigma^2\right)$$
$$\sigma = \left(\frac{100 - \text{Control Rating}}{100}\right) \times 0.25 \text{ ft}$$

- **High Control Pitcher (Rating 90)**: $\sigma \approx 0.025 \text{ ft}$ ($\approx 0.3 \text{ inches}$ variance). Target precision is surgical.
- **Low Control Pitcher (Rating 60)**: $\sigma \approx 0.100 \text{ ft}$ ($\approx 1.2 \text{ inches}$ variance). High chance of missing over the heart or into the dirt.

If $|\Delta x| > 0.12 \text{ ft}$ or $|\Delta y| > 0.12 \text{ ft}$, the actual arrival zone jumps to the adjacent zone based on the directional gradient.

---

## 7. App UI Synchronization & Live Update Mechanism

This document is bidirectionally linked with the running web application and API:

1. **Read Live Documentation**:
   - `GET /api/pitching-logic` returns the current markdown text, parsed configuration rules, file size, and last modified date.
2. **Update Documentation & Active Engine Rules**:
   - `PUT /api/pitching-logic` accepts updated markdown content.
   - The server validates the content, writes it directly to `/pitching_logic.md`, parses the `rules_config` JSON block, and hot-reloads the simulation weights in the running engine without restarting the server.
3. **Interactive UI Features**:
   - **Rich Markdown Viewer & In-App Editor**: Allows direct edits to text, formulas, and weight matrices.
   - **Quick Rule Multiplier Sliders**: Tune Double Play, 2-Strike, or Hot Zone weights visually, with immediate auto-sync to this document and the live pitching engine.

---

## 8. Batter Aggressiveness & Swing Decision Model

To mirror the pitcher's tactical intent system, the batter evaluates each incoming delivery through a count-dependent aggression framework. Standard MLB Statcast data shows that batters do **not** swing with static 90%+ probabilities across zones—especially on early counts or when working deep counts.

### A. Count-Dependent Mindsets & Tendencies

| Count State | Batter Approach Regime | Heart Zone Swing % | Corner / Edge % | Chase Zone % | Strategic Mindset & Take Dynamics |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **0-0 (First Pitch)** | `FIRST_PITCH_TAKE_PROBE` | ~52% - 58% | ~24% - 30% | ~8% - 12% | **Take Tendency High**: Hitters take ~45-50% of heart pitches to track release point, velocity, and plane. If `FIRST_PITCH_TAKE` sign is given, swing drops to 5%. |
| **3-0 (Hitter's Walk Advantage)** | `THREE_OH_RED_LIGHT` | ~12% - 16% | ~4% - 6% | ~1% - 2% | **Automatic Red Light**: Strict take sign enforced. Forcing pitcher to throw consecutive strikes, maximizing on-base percentage and pitcher fatigue. |
| **0-2, 1-2 (Two Strikes)** | `TWO_STRIKE_PROTECT` | ~90% - 94% | ~76% - 82% | ~44% - 54% | **Plate Protection**: Strike zone expansion. Batter must protect against called strike 3; higher vulnerability to breaking balls in chase corridors. |
| **2-0, 3-1 (Hitter's Count)** | `COUNT_AMBUSH` | ~84% - 88% | ~42% - 48% | ~10% - 16% | **Selective Ambush**: Sitting dead-red on fastball in primary wheelhouse/hot-zone. Disciplined takes against offspeed and chase zones. |
| **0-1, 1-1, 2-1 (Neutral)** | `BALANCED_DISCIPLINED` | ~64% - 70% | ~40% - 46% | ~18% - 24% | **Balanced Battle**: Patiently probing the zone while punishing middle mistakes. |

### B. Dynamic Swing Probability Equation:
$$P(\text{Swing}) = P_{\text{base}}(\text{Zone}, \text{Batter Hot-Zone}) \times M_{\text{count}} \times M_{\text{approach}} \times M_{\text{discipline}}$$

Where:
- $M_{\text{count}}(0\text{-}0) = 0.58$ (first pitch take discount)
- $M_{\text{count}}(3\text{-}0) = 0.14$ (red light take suppression)
- $M_{\text{count}}(\text{Two Strikes}) = 1.25$ in-zone, $1.65$ chase expansion
- $M_{\text{approach}}(\text{TAKE\_ALL\_THE\_WAY}) = 0.05$ (dugout take sign)

---

## 9. Algorithm Specification: Plate Appearance Hidden Value Model (PA-HVM)

This algorithm measures the **hidden run value** an out produces for an offensive lineup by decoupling overall base-out changes into situational baselines, pitcher stamina degradation, and tactical intelligence.

### Core Data Structures & State

1. **Base-Out State**: A 4-tuple comprising the current out count ($0 \le \text{outs} \le 2$) and boolean occupancy flags for first, second, and third base $(B_1, B_2, B_3)$.
2. **State Indexing Function**: Base-out configurations map directly to a static 24-element Run Expectancy array (RE24) via a 3-bit binary mask:
   $$\text{index} = (\text{outs} \times 8) + (B_1 ? 1 : 0) + (B_2 ? 2 : 0) + (B_3 ? 4 : 0)$$
   Any transition reaching $\text{outs} \ge 3$ yields $RE = 0.0$.

#### 24-Element Static Run Expectancy Matrix (RE24)

```
+------------+-------+-------+-------+-------+-------+-------+-------+-------+
| Base State |  ---  | 1B--  | -2B-  | 1B-2B | --3B  | 1B-3B | -2B3B | Loaded|
| Bit Mask   |   0   |   1   |   2   |   3   |   4   |   5   |   6   |   7   |
+------------+-------+-------+-------+-------+-------+-------+-------+-------+
| 0 Outs     | 0.481 | 0.859 | 1.100 | 1.437 | 1.350 | 1.784 | 1.964 | 2.292 |
| 1 Out      | 0.254 | 0.509 | 0.664 | 0.884 | 0.950 | 1.130 | 1.376 | 1.520 |
| 2 Outs     | 0.098 | 0.214 | 0.305 | 0.429 | 0.353 | 0.478 | 0.570 | 0.736 |
+------------+-------+-------+-------+-------+-------+-------+-------+-------+
```

### Evaluation Pipeline

Given an initial state $S_{\text{pre}}$, a resulting state $S_{\text{post}}$, and plate appearance context (pitches seen $P$, cumulative pitch count $C$, starter ERA $E_{\text{start}}$, and bullpen ERA $E_{\text{pen}}$):

#### 1. Situational Value ($\Delta V_{\text{sit}}$)
Isolates execution from the standard penalty of making an out:
- Compute the actual run expectancy shift:
  $$\Delta RE_{\text{actual}} = RE(S_{\text{post}}) - RE(S_{\text{pre}}) + \text{runs\_scored}$$
- Define the unproductive baseline ($S_{\text{base}}$) as incrementing the out count by 1 while holding all runners stationary:
  $$\Delta RE_{\text{base}} = RE(S_{\text{base}}) - RE(S_{\text{pre}})$$
- Calculate situational delta:
  $$\Delta V_{\text{sit}} = \Delta RE_{\text{actual}} - \Delta RE_{\text{base}}$$
  *(An out that advances runners yields a positive credit by outperforming the unproductive baseline).*

#### 2. Pitch Fatigue & Reliever Acceleration ($\Delta V_{\text{fatigue}}$)
Quantifies physical wear and early rotation exposure:
- Calculate excess pitches relative to league average ($\bar{P} \approx 3.9$):
  $$P_{\text{diff}} = P - 3.9$$
- Apply stamina penalty coefficient ($k_{\text{fatigue}} = 0.0042$), scaled by a fatigue multiplier ($1.45\times$) if the pitcher's cumulative count exceeds the designated threshold ($C > 75$):
  $$\Delta V_{\text{pitch\_fatigue}} = P_{\text{diff}} \times k_{\text{fatigue}} \times (C > 75 \ ? \ 1.45 : 1.0)$$
- If $P_{\text{diff}} > 0$ against a starting pitcher, compute the value of accelerated bullpen deployment based on the run-prevention delta:
  $$\Delta V_{\text{pen}} = P_{\text{diff}} \times \frac{\max(0, E_{\text{pen}} - E_{\text{start}})}{1000}$$
- Sum stamina components:
  $$\Delta V_{\text{fatigue}} = \Delta V_{\text{pitch\_fatigue}} + \Delta V_{\text{pen}}$$

#### 3. Lineup Tactical Intel ($\Delta V_{\text{intel}}$)
Models information gain for subsequent hitters:
- If the plate appearance reaches a deep threshold ($P \ge 6$), credit run value proportional to unique pitch types observed ($T$):
  $$\Delta V_{\text{intel}} = k_{\text{intel}} \times (T - 1) \quad (\text{with } k_{\text{intel}} = 0.015)$$
- Otherwise, $\Delta V_{\text{intel}} = 0.0$.

#### 4. Net Aggregation
$$\Delta V_{\text{hidden}} = \Delta V_{\text{sit}} + \Delta V_{\text{fatigue}} + \Delta V_{\text{intel}}$$

### Implementation Invariants
- **Decoupled Lookups**: The calculation requires only $O(1)$ state lookups via direct array masking indexing.
- **Sign Conventions**: $\Delta RE_{\text{actual}}$ reflects traditional box-score impact (typically negative on an out), while $\Delta V_{\text{sit}}$ reflects net contribution relative to an unproductive out baseline (non-negative on productive advances).

