# 05. React & JS Front-End Integration

## Front-End Architecture

The front-end architecture is built to provide zero-latency tactile feedback, interactive zone selection, and smooth trajectory rendering while maintaining absolute contract parity with the authoritative backend and Android Jetpack Compose clients.

```
┌─────────────────────────────────────────────────────────────┐
│                 Front-End Client (Web / React)              │
│                                                             │
│   ┌──────────────────────┐      ┌───────────────────────┐   │
│   │ Interactive Zone Grid│      │ Pitch Intent & Type   │   │
│   │ (SVG Click Target)   │      │ Selector Controls     │   │
│   └──────────┬───────────┘      └───────────┬───────────┘   │
│              │                              │               │
│              ▼                              ▼               │
│   ┌─────────────────────────────────────────────────────┐   │
│   │       Optimistic State & Action Dispatcher          │   │
│   │       • POST /api/pitch                             │   │
│   │       • POST /api/sim_at_bat                        │   │
│   └──────────────────────────┬──────────────────────────┘   │
└──────────────────────────────┼──────────────────────────────┘
                               │ HTTP REST Payload
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Authoritative Server                     │
│   1. Calculates Statcast Trajectory & Break Vectors         │
│   2. Evaluates Batter Collision & Umpire Decision           │
│   3. Records Pitch/At-Bat in Persistent Database            │
│   4. Returns Updated GameState & PitchTelemetry             │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Client Reactive Visual Updates              │
│   • SVG Ball Flight Path & Landing Pulse                    │
│   • Scoreboard (Count, Balls, Strikes, Outs, Score)         │
│   • Matchup Card (ERA, WHIP, Today's Lines)                 │
│   • Live Database Roster Synchronization                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Front-End Components

### 1. The Interactive Strike Zone Component
The strike zone is rendered as an SVG canvas featuring:
- **Rulebook Strike Zone**: Centered box with subtle grid lines representing the 9 inner zones.
- **Chase Corridors**: Outer clickable borders allowing pitchers to select chase targets outside the box.
- **Batter Hot Zone Heatmap Overlays**: Semitransparent color fills showing cold zones (blue) and hot zones (red) based on the current batter.
- **Click Event Handlers**: Clicking any cell maps directly to the zone identifier and updates the selected target in real time.

```javascript
zoneElement.addEventListener('click', () => {
  const selectedZone = zoneElement.dataset.zone;
  highlightSelectedZone(selectedZone);
  document.getElementById('target-zone-display').textContent = selectedZone;
});
```

### 2. Pitch Flight Animation Engine
When a pitch response arrives from `/api/pitch`, the client renders a visual trajectory:
1. **Pitch Trail**: An SVG curved bezier line that curves according to `vertical_break_in` and `horizontal_break_in`.
2. **Impact Indicator**: A pulsating circle drawn at $(x_{svg}, y_{svg})$, colored green for a strike or amber for a ball.
3. **Statcast Velocity Badge**: Displays the radar gun readout (e.g. `98.4 MPH`) with pitch-type label and spin rate.

### 3. State Reactivity & UI Bindings
All DOM elements are tied to the authoritative `gameState` returned by the server:
- **Scoreboard**: `document.getElementById('sb-count').textContent = "${balls}-${strikes}"`.
- **Base Diamond**: Runners on first, second, and third light up dynamically.
- **Pitch Telemetry HUD**: Shows speed, spin, break, and outcome description.
- **Pitch History Feed**: Appends every completed pitch with pitch count, result badge, and description.

---

## Contract Parity with Android Jetpack Compose

The web front-end and Android mobile app consume identical data models:
- Pitch Request: `{ pitch_intent: "STRIKE" | "CHASE" | "WASTE" | "CORNER", pitch_type: string, zone?: string }`
- Game Response: `{ status: "success", pitch: PitchEvent, game: GameState }`

This shared contract guarantees that behavior, physics calculations, and game outcomes are completely indistinguishable between platforms.
