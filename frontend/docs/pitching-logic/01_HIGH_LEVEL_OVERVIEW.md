# 01. High-Level Pitching Logic Overview

## Executive Summary

The pitching engine simulates modern Major League Baseball Statcast mechanics with deterministic mathematical precision. Rather than using simple random number generators or visual approximations, every pitch executed in the web client and Android application follows a rigorous six-stage pipeline:

```
[1. Situation & Count Context]
              │
              ▼
[2. Intent & Tactical Strategy Selection]
              │
              ▼
[3. Repertoire & Pitch Selection]
              │
              ▼
[4. Command Targeting & Statcast Physics Execution]
              │
              ▼
[5. Batter Reaction & Collision Resolution]
              │
              ▼
[6. State Synchronization & Database Telemetry]
```

---

## The Six-Stage Simulation Pipeline

### Stage 1: Situation & Count Context
Before a pitch is initiated, the engine reads the active game state:
- **Count**: Number of balls and strikes (e.g. `0-2` put-away vs. `3-1` hitter's count).
- **Base State**: Runners on first, second, or third (e.g., runner on first with $< 2$ outs triggers double-play hunting).
- **Outs**: Out count determining risk tolerance and run-scoring urgency.
- **Score Differential**: Determines Win Probability and Pitch Leverage Index (LI).

### Stage 2: Intent & Tactical Strategy
The pitcher selects an **Intent**:
- **STRIKE**: Prioritizes filling the strike zone with high-velocity 4-seamers or sinkers.
- **CHASE**: Expands the zone off the edges (typically lower-away or chase-away) using high-whiff breaking balls (Sweeper or Curveball).
- **WASTE**: Intentionally unhittable pitch thrown outside to reset timing or exploit an over-aggressive hitter.
- **CORNER**: Surgical targeting of the black border of the strike zone, maximizing called strikes while minimizing sweet-spot contact.

### Stage 3: Repertoire & Pitch Selection
The pitcher's repertoire (e.g. Nolan McLean's 4-Seam Fastball, Spin Monster Sweeper, Power Sinker, Spike Curveball) is ranked dynamically based on:
1. Pitcher ratings (Velocity, Spin, Control, Break).
2. Batter tendencies (Hot zones vs. cold zones).
3. Count context weights (Fastballs weighted heavily behind in count; Sweepers weighted heavily ahead with two strikes).

### Stage 4: Statcast Aerodynamics & Command Variance
Once a pitch and target zone are chosen:
- **Velocity ($v$)**: Sampled within the pitch's characteristic velocity envelope (e.g. $96.5 - 99.5$ mph for 4-seamers).
- **Spin Rate ($\omega$)**: Sampled within the aerodynamic profile (e.g. $2950 - 3080$ RPM for sweepers).
- **Break Vectors ($\Delta x_{break}, \Delta y_{break}$)**: Aerodynamic vertical and horizontal deflection caused by the Magnus effect.
- **Command Quality & Jitter**: The pitch does not hit the exact center of the target zone. A bivariate Gaussian jitter error vector $(\delta_x, \delta_y)$ is applied based on the pitcher's Control rating ($82/100$) and pitch intent.

### Stage 5: Batter Reaction & Collision Resolution
The final $(\text{Statcast } x, y)$ coordinate determines zone membership:
- If inside the 9-cell inner zone: **Called Strike** or **In-Zone Swing**.
- If in the 4 exterior chase corridors: **Ball** or **Chase Swing**.
- Batter swing decisions are influenced by pitch tunneling, velocity, and whether the pitch crosses a hot zone (e.g. Aaron Judge heart of plate = $92\%$ swing probability and elevated exit velocity).

### Stage 6: State Synchronization & Database Telemetry
When the pitch concludes:
1. Game state (count, outs, score, base runners) updates authoritatively.
2. Pitch event is recorded in the pluggable database adapter (`db.recordPitch` / `db.recordAtBat`).
3. Pitcher game metrics (pitch count, strikes, balls) and season rates (ERA, WHIP) update atomically.
4. Batter slash lines (AVG, OBP, SLG, OPS) recalculate instantly.
5. The web front-end and Android Compose UI receive the synchronized payload and update visuals smoothly.
