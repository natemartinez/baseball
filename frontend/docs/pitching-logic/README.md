# Pitching Logic & Physics Engine Documentation

Welcome to the architectural documentation for the **Baseball Simulation Client** pitching engine. This folder contains high-level and granular technical explanations of how pitching mechanics, Statcast aerodynamics, strategic AI intent, strike zone command, front-end React/JS rendering, and persistent database statistics operate together.

---

## 📚 Table of Contents

| Document | Topic | Description |
| :--- | :--- | :--- |
| [01. High-Level Overview](01_HIGH_LEVEL_OVERVIEW.md) | High-Level Architecture | End-to-end simulation lifecycle, from pitcher intent to UI delivery and database update. |
| [02. Statcast Physics & Arsenal](02_STATCAST_PHYSICS_AND_ARSENAL.md) | Aerodynamics & Repertoire | Velocity bands, spin rates, aerodynamic break, Stuff+ ratings, and pitch profiles. |
| [03. Intent & Strategy Matrix](03_INTENT_AND_STRATEGY_MATRIX.md) | AI Decision Engine | Leverage calculations, count context (ahead/behind/full), double-play hunts, and hot-zone avoidance. |
| [04. Strike Zone Command & Targeting](04_STRIKE_ZONE_COMMAND_AND_TARGETING.md) | 13-Zone Coordinate Model | Inner strike zone, shadow/chase rings, Gaussian command jitter, and umpire call determination. |
| [05. React & JS Front-End Integration](05_REACT_JS_FRONTEND_INTEGRATION.md) | Client Architecture | Reactive state updates, SVG strike zone coordinate mapping, and flight path rendering. |
| [06. Database & Persistent Telemetry](06_DATABASE_PERSISTENCE_INTEGRATION.md) | Persistence Architecture | Atomic recalculation of ERA, WHIP, AVG, and OPS across mock and PostgreSQL adapters. |

---

## 🔄 Live Interactive Documentation Integration

This documentation is not a static text artifact. It is connected directly to the running server engine:

1. **Live REST Endpoints**:
   - `GET /api/docs`: Returns machine-readable documentation metadata and active engine configuration.
   - `GET /api/docs/file?name=01_HIGH_LEVEL_OVERVIEW.md`: Streams raw or formatted markdown files directly.
   - `POST /api/docs/simulate-step-by-step`: Executes the mathematical pitching pipeline step-by-step and returns intermediate calculations (velocity, spin, command jitter, coordinates, swing probability, outcome).

2. **Client-Side Interactive Sandbox**:
   - An interactive documentation viewer and step-by-step pitch calculator is embedded directly into the web application.
   - Developers and coaches can modify pitch types, intents, and target zones to inspect how each mathematical phase reacts in real time.

3. **Continuous Parity**:
   - As new pitch types, batter ratings, or physics formulas are updated in `server.js` or Kotlin Android models, the documentation automatically reflects the running state without desynchronization.
