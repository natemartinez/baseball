# 02. Statcast Aerodynamics & Pitch Repertoire

## Physics Model: The Magnus Force and Trajectory Mechanics

In modern Statcast tracking, baseball trajectories are determined by three forces:
1. **Gravity ($F_g = mg$)**: Uniform downward acceleration of $-32.174 \text{ ft/s}^2$.
2. **Aerodynamic Drag ($F_D = \frac{1}{2} C_D \rho A v^2$)**: Resists forward ball movement from the rubber ($60.5\text{ ft}$) to home plate ($1.4\text{ ft}$ release extension).
3. **Magnus Lift/Deflection ($F_M = \frac{1}{2} C_L \rho A v^2 \cdot (\hat{\omega} \times \hat{v})$)**: Spin-induced lateral and vertical trajectory deflection.

$$\vec{a}_{total} = \vec{g} - \frac{F_D}{m} \hat{v} + \frac{F_M}{m} (\hat{\omega} \times \hat{v})$$

---

## Pitch Profiles in the Simulation Engine

The engine defines canonical physical profiles for each pitch in the pitcher's arsenal:

```javascript
const pitchProfiles = {
  "Spin Monster Sweeper": {
    velocityRange: [83.0, 86.0],       // mph
    spinRateRange: [2950, 3080],       // rpm (elite spin tier)
    verticalBreak: [-26, -34],         // inches of drop
    horizontalBreak: [-14, -19],       // inches of sweep (glove-side)
    statcast: {
      whiff_pct: 44.5,
      chase_pct: 39.0,
      gb_pct: 38.0,
      stuff_plus: 135,
      zone_pct: 42.5,
      run_value: 8.4
    }
  },
  "Four-Seam Fastball": {
    velocityRange: [96.5, 99.5],       // mph (high heat)
    spinRateRange: [2420, 2540],       // rpm
    verticalBreak: [-12, -15],         // "rising" visual effect (low drop)
    horizontalBreak: [5, 8],           // inches of arm-side run
    statcast: {
      whiff_pct: 27.0,
      chase_pct: 22.5,
      gb_pct: 32.0,
      stuff_plus: 118,
      zone_pct: 64.0,
      run_value: 4.2
    }
  },
  "Power Sinker": {
    velocityRange: [95.0, 98.2],       // mph
    spinRateRange: [2180, 2300],       // rpm
    verticalBreak: [-20, -25],         // heavy downward bite
    horizontalBreak: [15, 20],         // massive arm-side run into righties
    statcast: {
      whiff_pct: 18.5,
      chase_pct: 28.0,
      gb_pct: 64.5,                   // elite groundball induction rate
      stuff_plus: 106,
      zone_pct: 58.0,
      run_value: 5.1
    }
  },
  "Spike Curveball": {
    velocityRange: [79.5, 83.0],       // mph
    spinRateRange: [2820, 2960],       // rpm (sharp topspin)
    verticalBreak: [-50, -58],         // 12-to-6 drop
    horizontalBreak: [-8, -13],        // slight glove-side sweep
    statcast: {
      whiff_pct: 38.0,
      chase_pct: 35.0,
      gb_pct: 48.0,
      stuff_plus: 122,
      zone_pct: 45.0,
      run_value: 3.8
    }
  }
};
```

---

## Tactical Pitch Roles

### 1. Spin Monster Sweeper (3000+ RPM)
- **Primary Use**: Two-strike putaway pitch against right-handed hitters and outside wipeout option against lefties.
- **Flight Signature**: Late, horizontal snap across the outer third of the plate.
- **Why It Works**: With a $44.5\%$ whiff rate and $135$ Stuff+, hitters frequently swing over the top of the horizontal plane.

### 2. Four-Seam Fastball (98 MPH)
- **Primary Use**: Establishing count early ($0-0$), challenging elevated zones with two strikes, or battling when behind in the count ($3-1$).
- **Flight Signature**: True backspin creating a high perceived elevation ("ride" through the top of the zone).
- **Zone Rate**: Highest in-zone command ($64\%$).

### 3. Power Sinker (64.5% Groundball Rate)
- **Primary Use**: Runner on first with $< 2$ outs to roll an inning-ending double play ($6-4-3$).
- **Flight Signature**: Tunnels like a four-seamer before dropping violently with $15-20$ inches of arm-side run.

### 4. Spike Curveball (Down-in-the-Zone Hammer)
- **Primary Use**: Changing eye levels and altering batter timing by nearly $18\text{ mph}$ relative to the fastball.
- **Drop**: Exceeds $50$ inches of total downward deflection including gravity.
