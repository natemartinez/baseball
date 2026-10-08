# 04. Strike Zone Command & 13-Zone Coordinate Model

## The 13-Zone Coordinate System

The simulation maps home plate and the strike zone onto a continuous 2D plane measured in Statcast feet, centered at the midpoint of home plate:
- **Horizontal Axis ($x$)**: Distance from the center of home plate in feet.
  - Plate width: $17\text{ inches} \approx 1.417\text{ ft}$ (edges at $x = \pm 0.708\text{ ft}$).
- **Vertical Axis ($y$)**: Distance from the ground in feet.
  - Typical strike zone height: $1.5\text{ ft}$ (hollow of the knee) to $3.5\text{ ft}$ (midpoint between shoulders and belt).

```
                      [ CHASE HIGH (y > 3.5) ]
        ┌───────────────────┬───────────────────┬───────────────────┐
        │     Upper-In      │   Upper-Middle    │    Upper-Away     │
        ├───────────────────┼───────────────────┼───────────────────┤
[ CHASE │     Middle-In     │       Heart       │    Middle-Away    │ [ CHASE
   IN   ├───────────────────┼───────────────────┼───────────────────┤   AWAY ]
(x<-0.7)│     Lower-In      │   Lower-Middle    │    Lower-Away     │ (x>+0.7)
        └───────────────────┴───────────────────┴───────────────────┘
                      [ CHASE LOW (y < 1.5) ]
```

---

## 13-Zone Metric Matrix

| Zone Identifier | Statcast Center ($x, y$ in ft) | Zone Type | Target Dimension |
| :--- | :--- | :--- | :--- |
| `upper-in` | $(-0.55, 3.15)$ | In-Zone (Strike) | $0.47\text{ ft} \times 0.67\text{ ft}$ |
| `upper-middle` | $(0.00, 3.15)$ | In-Zone (Strike) | $0.47\text{ ft} \times 0.67\text{ ft}$ |
| `upper-away` | $(+0.55, 3.15)$ | In-Zone (Strike) | $0.47\text{ ft} \times 0.67\text{ ft}$ |
| `middle-in` | $(-0.55, 2.50)$ | In-Zone (Strike) | $0.47\text{ ft} \times 0.67\text{ ft}$ |
| `heart` | $(0.00, 2.50)$ | In-Zone (Strike) | $0.47\text{ ft} \times 0.67\text{ ft}$ |
| `middle-away` | $(+0.55, 2.50)$ | In-Zone (Strike) | $0.47\text{ ft} \times 0.67\text{ ft}$ |
| `lower-in` | $(-0.55, 1.85)$ | In-Zone (Strike) | $0.47\text{ ft} \times 0.67\text{ ft}$ |
| `lower-middle` | $(0.00, 1.85)$ | In-Zone (Strike) | $0.47\text{ ft} \times 0.67\text{ ft}$ |
| `lower-away` | $(+0.55, 1.85)$ | In-Zone (Strike) | $0.47\text{ ft} \times 0.67\text{ ft}$ |
| `chase-high` | $(0.00, 3.85)$ | Chase (Ball) | $y > 3.5\text{ ft}$ |
| `chase-low` | $(0.00, 1.15)$ | Chase (Ball) | $y < 1.5\text{ ft}$ |
| `chase-in` | $(-1.05, 2.50)$ | Chase (Ball) | $x < -0.708\text{ ft}$ |
| `chase-away` | $(+1.05, 2.50)$ | Chase (Ball) | $x > +0.708\text{ ft}$ |

---

## Command Jitter & Gaussian Error Modeling

Even elite pitchers cannot deliver a baseball to the exact mathematical center of a target cell. The actual pitch arrival location $(x_{final}, y_{final})$ incorporates command error:

$$\begin{aligned}
x_{final} &= x_{target} + \delta_x \\
y_{final} &= y_{target} + \delta_y
\end{aligned}$$

Where the error vector $(\delta_x, \delta_y)$ is derived from the pitcher's **Control Rating**:

$$\sigma_{command} = \frac{100 - \text{Control Rating}}{100} \times \sigma_{base}$$

- **High Control Pitcher (Rating 82)**: Tight variance ($\sigma \approx 0.12\text{ ft}$ / $1.4\text{ inches}$). Near-misses clip zone edges.
- **Low Control Pitcher (Rating 50)**: Wide variance ($\sigma \approx 0.28\text{ ft}$ / $3.4\text{ inches}$). High risk of missing over the heart of the plate or completely out of the zone.

### Intent Displacement Rules
1. **`STRIKE` Intent**:
   - Target point is biased toward the center of the selected zone.
   - Command variance is clipped so that over $75\%$ of intended strikes remain in-zone.
2. **`CHASE` Intent**:
   - Target point is nudged $3-6\text{ inches}$ beyond the outer boundary of the strike zone.
3. **`WASTE` Intent**:
   - Displaced by $> 1.0\text{ ft}$ outside the zone, eliminating any chance of umpire strike calls or batter swings.

---

## SVG Viewport Coordinate Conversion

For the web interface and Jetpack Compose canvas:
- SVG Width: $240\text{ px}$ (centered at $x_{svg} = 120\text{ px}$).
- SVG Height: $280\text{ px}$ (plate surface at $y_{svg} = 260\text{ px}$).

```javascript
function statcastToSvgCoordinates(locX, locY) {
  // locX: [-1.5 ft, +1.5 ft] -> SVG [0 px, 240 px]
  const svgX = 120 + (locX / 1.5) * 100;
  // locY: [0.5 ft, 4.5 ft] -> SVG [280 px, 0 px]
  const svgY = 280 - ((locY - 0.5) / 4.0) * 260;
  return { svgX, svgY };
}
```
