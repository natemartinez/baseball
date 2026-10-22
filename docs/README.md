# Documentation

System-design documentation for the Baseball Simulation project.

## Implemented

- [3D Field, Pitch Visualization & HUD](./08_3D_FIELD_PITCH_AND_HUD.md) — field geometry, coordinate systems, camera calibration, projected strike-zone HUD, mock pitch data flow, and IVB kinematics.

## Planned

The following areas still need dedicated documents:

- Architecture overview and deployment topology
- SQLite schema and seed-data lifecycle
- REST API contracts and error envelopes
- Game state machines (inning, count, outs, bases, at-bat)
- Backend Statcast execution and command model
- Frontend service/store architecture and mock/live parity
- Developer runbook, CI, and visual-regression strategy
- Architecture decision records (ADRs) for camera, HUD, and physics choices

Until those are written, this page is the authoritative index for tracked documentation. Product and run instructions remain in the repository root [`README.md`](../README.md).
