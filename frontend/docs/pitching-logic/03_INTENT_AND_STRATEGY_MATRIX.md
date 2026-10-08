# 03. Intent & Strategy Decision Matrix

## Decision Engine Overview

The pitching engine utilizes a probabilistic decision tree and weighting algorithm that continuously evaluates game context to select the optimal pitch intent, repertoire weapon, and zone target.

```
┌────────────────────────────────────────────────────────┐
│               Game Context Evaluation                  │
│  • Balls & Strikes (Ahead, Behind, Full Count)         │
│  • Base Runners (Bases Empty, Double Play, Loaded)     │
│  • Batter Heatmap (Slugging against 13 zones)          │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│             Intent & Strategy Selection                │
│  • NEUTRAL_PITCH_MIX (0-0, 1-1)                        │
│  • TWO_STRIKE_PUT_AWAY (0-2, 1-2)                      │
│  • CRITICAL_ZONE_CHALLENGE (3-0, 3-1)                  │
│  • DOUBLE_PLAY_GROUNDER_HUNT (Runner on 1st, <2 outs)  │
│  • BASES_LOADED_PUNCHOUT / COMMAND_STRIKE              │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│            Dynamic Repertoire & Zone Weights           │
│  Repertoire: Sweeper (44.5%), Fastball (27%), Sinker   │
│  Zone: Lower-Away (Cold), Heart (Penalized), Chase     │
└────────────────────────────────────────────────────────┘
```

---

## The Four Pitch Intents

1. **`STRIKE`**:
   - **Objective**: Fill the strike zone and secure a called or swinging strike.
   - **Targeting**: Concentrated in the 9 inner zones.
   - **Error Handling**: Jitter is constrained inward so near-misses remain within the rulebook strike zone.

2. **`CHASE`**:
   - **Objective**: Bait the hitter into swinging at a pitch outside the strike zone with two strikes.
   - **Targeting**: Directed toward exterior chase corridors (e.g. `chase-away` or `chase-low`).
   - **Hitter Reaction**: Takes into account batter chase percentage and pitch break profile.

3. **`WASTE`**:
   - **Objective**: Deliberately throw an unhittable pitch off the plate (e.g. on `0-2` to waste a pitch or alter timing).
   - **Swing Probability**: Batter swing probability is set to $0.0\%$, guaranteeing a ball while pushing count to `1-2`.

4. **`CORNER`**:
   - **Objective**: Paint the peripheral shadow zone of home plate.
   - **Execution**: Lower risk of extra-base contact while preserving strike potential if framed well by the catcher.

---

## Situational Strategy Multipliers

### 1. Double Play Situation (Runner on 1st, $< 2$ Outs)
- **Primary Goal**: Induce a weak downward grounder toward shortstop or second base.
- **Pitch Multipliers**:
  - **Power Sinker Weight**: Multiplied by $\times 2.8$ (due to $64.5\%$ groundball rate).
  - **Spike Curveball Weight**: Multiplied by $\times 1.3$.
  - **Four-Seam Fastball Weight**: Reduced to $\times 0.45$.
- **Zone Multipliers**:
  - `lower-in`, `lower-middle`, `lower-away`: Multiplied by $\times 3.0$.
  - `chase-low`: Multiplied by $\times 2.6$.
  - `upper-*` and `chase-high`: Penalized to $\times 0.30$.

### 2. Ahead in the Count (Strikes $= 2$)
- **Primary Goal**: Generate a swinging strikeout (whiff) without giving up contact.
- **Pitch Multipliers**:
  - **Spin Monster Sweeper**: Multiplied by $\times 3.0$ ($44.5\%$ whiff rate, $3000$ RPM).
  - **Spike Curveball**: Multiplied by $\times 2.0$.
  - **Fastball**: Reduced to $\times 0.55$.
- **Zone Multipliers**:
  - Chase zones (`chase-away`, `chase-low`): Multiplied by $\times 3.4$.
  - `heart`: Heavily penalized to $\times 0.12$.

### 3. Behind in the Count (Balls $= 3$, Strikes $< 2$)
- **Primary Goal**: Prevent a free pass (walk) while minimizing barrel contact.
- **Pitch Multipliers**:
  - **Four-Seam Fastball**: Multiplied by $\times 2.6$ ($64\%$ zone rate).
  - **Power Sinker**: Multiplied by $\times 1.9$.
  - **Sweeper**: Deprioritized to $\times 0.35$.
- **Zone Multipliers**:
  - In-zone strikes: Multiplied by $\times 2.0$.
  - Chase corridors: Suppressed to $\times 0.12$.

---

## Batter Heatmap Integration (Aaron Judge Profile)

The pitcher adjusts zone targeting to avoid the batter's high-damage zones:

| Zone | Judge Career Slugging | Zone Type | Strategic Multiplier |
| :--- | :--- | :--- | :--- |
| **Heart** | `.820` | Hot (Danger) | Down-weighted by $\times 0.22$ |
| **Upper-In** | `.650` | Hot | Down-weighted by $\times 0.22$ |
| **Middle-In** | `.540` | Hot | Down-weighted by $\times 0.22$ |
| **Lower-Middle** | `.420` | Neutral | Standard Weight |
| **Middle-Away** | `.280` | Cold (Target) | Boosted by $\times 2.4$ |
| **Lower-Away** | `.240` | Cold (Target) | Boosted by $\times 2.4$ |
| **Chase Outer Ring** | `.120 - .180` | Chase | Boosted with 2 strikes |
