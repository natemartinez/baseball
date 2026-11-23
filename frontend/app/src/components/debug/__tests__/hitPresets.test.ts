import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  HIT_PRESETS,
  buildActiveBattedBallFromPreset,
  generateKinematicGrounder,
  generateAerodynamicFlight,
  computeBattedBallTrajectory,
} from '../hitPresets';

describe('Hit Presets for Debug Launcher', () => {
  it('provides all 5 core contact archetypes', () => {
    const ids = HIT_PRESETS.map((p) => p.id);
    assert.ok(ids.includes('ss_chopper'));
    assert.ok(ids.includes('1b_grounder'));
    assert.ok(ids.includes('line_drive_gap'));
    assert.ok(ids.includes('fly_ball_rf'));
    assert.ok(ids.includes('moonshot_hr'));
  });

  it('validates ss_chopper grounder characteristics', () => {
    const chopper = HIT_PRESETS.find((p) => p.id === 'ss_chopper')!;
    assert.equal(chopper.isGrounder, true);
    assert.ok(chopper.launchAngle <= 10);
    assert.equal(chopper.samples.length, 20);

    // Initial sample starts near home plate at contact height
    assert.ok(Math.abs(chopper.samples[0][0]) < 1.0);
    assert.ok(Math.abs(chopper.samples[0][1]) < 1.0);
    assert.ok(chopper.samples[0][2] >= 2.5);

    // Ending sample lands near shortstop (-129.8, 399.4, 0)
    const last = chopper.samples[chopper.samples.length - 1];
    assert.ok(last[0] < -20);
    assert.ok(last[1] > 60);
    assert.equal(last[2], 0);
  });

  it('validates 1b_grounder characteristics', () => {
    const grounder = HIT_PRESETS.find((p) => p.id === '1b_grounder')!;
    assert.equal(grounder.isGrounder, true);
    assert.ok(grounder.launchAngle <= 10);
    assert.equal(grounder.samples.length, 20);

    const last = grounder.samples[grounder.samples.length - 1];
    assert.ok(last[0] > 40);
    assert.ok(last[1] > 50);
    assert.equal(last[2], 0);
  });

  it('validates fly_ball_rf and moonshot_hr apex elevation', () => {
    const flyBall = HIT_PRESETS.find((p) => p.id === 'fly_ball_rf')!;
    assert.equal(flyBall.isGrounder, false);
    assert.ok(flyBall.apexHeight >= 60);

    const moonshot = HIT_PRESETS.find((p) => p.id === 'moonshot_hr')!;
    assert.equal(moonshot.isGrounder, false);
    assert.ok(moonshot.apexHeight >= 100);
    assert.ok(moonshot.distance >= 400);
  });

  it('calibrates ss_chopper and 1b_grounder samples to terminate at intercept point', () => {
    const ss = HIT_PRESETS.find((p) => p.id === 'ss_chopper')!;
    assert.ok(ss.hangTime <= 1.8, `Expected ss.hangTime <= 1.8, got ${ss.hangTime}`);
    assert.ok(ss.distance < 140, `Expected ss.distance < 140, got ${ss.distance}`);
    const lastSample = ss.samples[ss.samples.length - 1];
    assert.ok(Math.abs(lastSample[0] - (-38.2)) < 1.0, `Expected x near -38.2, got ${lastSample[0]}`);
    assert.ok(Math.abs(lastSample[1] - 108.5) < 1.0, `Expected y near 108.5, got ${lastSample[1]}`);
    assert.equal(lastSample[2], 0);

    const b1 = HIT_PRESETS.find((p) => p.id === '1b_grounder')!;
    assert.ok(b1.hangTime <= 1.5, `Expected b1.hangTime <= 1.5, got ${b1.hangTime}`);
    assert.ok(b1.distance < 100, `Expected b1.distance < 100, got ${b1.distance}`);
    const lastB1 = b1.samples[b1.samples.length - 1];
    assert.ok(Math.abs(lastB1[0] - 58.4) < 1.0, `Expected x near 58.4, got ${lastB1[0]}`);
    assert.ok(Math.abs(lastB1[1] - 60.1) < 1.0, `Expected y near 60.1, got ${lastB1[1]}`);
    assert.equal(lastB1[2], 0);
  });

  it('builds a valid ActiveBattedBallData object with unique id', () => {
    const preset = HIT_PRESETS[0];
    const data = buildActiveBattedBallFromPreset(preset, 42);

    assert.equal(data.id, `debug-hit-${preset.id}-42`);
    assert.equal(data.hangTime, preset.hangTime);
    assert.equal(data.isGrounder, preset.isGrounder);
    assert.deepEqual(data.landingPos, preset.landingPos);
    assert.equal(data.samples.length, 20);
  });

  it('equips all presets with authentic fielding metadata', () => {
    const ssChopper = HIT_PRESETS.find((p) => p.id === 'ss_chopper');
    assert.ok(ssChopper);
    assert.equal(ssChopper.fielded, true);
    assert.equal(ssChopper.fielderId, 'SS');
    assert.equal(ssChopper.fieldingType, 'GROUND_SCOOP');
    assert.ok(Array.isArray(ssChopper.fielderStart));
    assert.ok(Array.isArray(ssChopper.interceptPoint));

    const grounder1B = HIT_PRESETS.find((p) => p.id === '1b_grounder');
    assert.ok(grounder1B);
    assert.equal(grounder1B.fielded, true);
    assert.equal(grounder1B.fielderId, '1B');
    assert.equal(grounder1B.fieldingType, 'BACKHAND_PICK');

    const gapDouble = HIT_PRESETS.find((p) => p.id === 'line_drive_gap');
    assert.ok(gapDouble);
    assert.equal(gapDouble.fielded, true);
    assert.equal(gapDouble.fielderId, 'LF');
    assert.equal(gapDouble.fieldingType, 'GROUND_SCOOP');

    const flyBallRF = HIT_PRESETS.find((p) => p.id === 'fly_ball_rf');
    assert.ok(flyBallRF);
    assert.equal(flyBallRF.fielded, true);
    assert.equal(flyBallRF.fielderId, 'RF');
    assert.equal(flyBallRF.fieldingType, 'ROUTINE_FLY_CATCH');

    const moonshot = HIT_PRESETS.find((p) => p.id === 'moonshot_hr');
    assert.ok(moonshot);
    assert.equal(moonshot.fielded, false);
    assert.equal(moonshot.fieldingType, 'HOME_RUN');

    // Also check buildActiveBattedBallFromPreset passes through fielding metadata
    const activeChopper = buildActiveBattedBallFromPreset(ssChopper, 1);
    assert.equal(activeChopper.fielded, true);
    assert.equal(activeChopper.fielderId, 'SS');
    assert.equal(activeChopper.fieldingType, 'GROUND_SCOOP');
    assert.deepEqual(activeChopper.fielderStart, ssChopper.fielderStart);
    assert.deepEqual(activeChopper.interceptPoint, ssChopper.interceptPoint);
  });

  describe('generateKinematicGrounder kinematics', () => {
    it('calculates natural shallow outfield rollout for 88 mph chopper', () => {
      const motion = generateKinematicGrounder(88, -5, -21.4);
      // Carries into shallow outfield at 233.1 ft
      assert.equal(motion.distance, 233.1);
      assert.ok(motion.hangTime >= 5.0 && motion.hangTime <= 6.0);
      assert.equal(motion.samples.length, 20);

      // Initial sample starts at contact height
      assert.ok(motion.samples[0][2] >= 2.5);

      // All elevation samples are non-negative
      for (const sample of motion.samples) {
        assert.ok(sample[2] >= 0.0);
      }

      // Final sample lands at turf level (z = 0) in shallow outfield (y > 200)
      const last = motion.samples[19];
      assert.equal(last[2], 0.0);
      assert.ok(last[1] > 200);

      // Demonstrates deceleration: distance covered in first quarter > 2x last quarter
      const dFirstQuarter = Math.hypot(motion.samples[5][0], motion.samples[5][1]);
      const dTotal = Math.hypot(last[0], last[1]);
      const dLastQuarter = dTotal - Math.hypot(motion.samples[14][0], motion.samples[14][1]);
      assert.ok(dFirstQuarter > 2.0 * dLastQuarter);
    });

    it('calculates natural shallow outfield rollout for 95 mph 1B grounder', () => {
      const motion = generateKinematicGrounder(95, 2, 32);
      assert.equal(motion.distance, 319.7);
      assert.ok(motion.hangTime >= 5.8 && motion.hangTime <= 6.5);

      const last = motion.samples[19];
      assert.equal(last[2], 0.0);
      assert.ok(last[1] > 200);
      assert.ok(last[0] > 100); // Slices toward right field line
    });

    it('stops weak dribbler naturally in the infield without reaching dirt arc', () => {
      const motion = generateKinematicGrounder(30, 0, 0);
      // Weak bunt/dribbler stops short in the infield grass (< 80 ft)
      assert.ok(motion.distance < 80);
      assert.ok(motion.hangTime < 4.0);
    });
  });

  describe('generateAerodynamicFlight aerodynamics', () => {
    it('calculates explosive exit velocity and trajectory for 104 mph line drive', () => {
      const flight = generateAerodynamicFlight(104, 16, -16);
      // Initial velocity off the bat: (s1 - s0) / delta_t >= 140 ft/s (> 95 mph off the bat)
      const dt = flight.hangTime / (flight.samples.length - 1);
      const ds = Math.hypot(flight.samples[1][0] - flight.samples[0][0], flight.samples[1][1] - flight.samples[0][1]);
      const initialSpeedFps = ds / dt;
      assert.ok(initialSpeedFps >= 140, `Initial speed ${initialSpeedFps} ft/s should be >= 140 ft/s`);

      // Hang time between 2.5s and 2.9s
      assert.ok(flight.hangTime >= 2.5 && flight.hangTime <= 2.9);
      // Distance carries into left-center gap (280 - 320 ft)
      assert.ok(flight.distance >= 280 && flight.distance <= 320);

      // All elevation samples are non-negative
      for (const sample of flight.samples) {
        assert.ok(sample[2] >= 0.0);
      }
      // Lands at turf level (z = 0)
      assert.equal(flight.samples[19][2], 0.0);
    });

    it('calculates authentic hang time, apex, and distance for 106 mph moonshot home run', () => {
      const flight = generateAerodynamicFlight(106, 32, 0);
      assert.ok(flight.hangTime >= 4.8 && flight.hangTime <= 5.3);
      assert.ok(flight.distance >= 400);
      assert.ok(flight.apexHeight >= 95 && flight.apexHeight <= 115);
      assert.equal(flight.samples[19][2], 0.0);
    });
  });

  describe('Exit Velocity & Transit Speed Verification', () => {
    it('verifies 95 mph grounder crosses the 90-ft baseline in <= 0.75s', () => {
      const grounder = HIT_PRESETS.find((p) => p.id === '1b_grounder')!;

      // Find the first sample crossing 90 ft horizontal distance from home plate
      let transitTime90Ft = grounder.hangTime;
      for (let i = 0; i < grounder.samples.length - 1; i++) {
        const dCurrent = Math.hypot(grounder.samples[i][0], grounder.samples[i][1]);
        const dNext = Math.hypot(grounder.samples[i + 1][0], grounder.samples[i + 1][1]);
        if (dNext >= 90) {
          const frac = (90 - dCurrent) / (dNext - dCurrent);
          const tCurrent = grounder.samples[i][3];
          const tNext = grounder.samples[i + 1][3];
          transitTime90Ft = tCurrent + frac * (tNext - tCurrent);
          break;
        }
      }

      assert.ok(
        transitTime90Ft <= 0.75,
        `95 mph grounder baseline crossing time ${transitTime90Ft.toFixed(3)}s exceeds 0.75s`,
      );
    });

    it('verifies both grounder presets terminate at infield fielder intercepts (< 140 ft)', () => {
      const chopper = HIT_PRESETS.find((p) => p.id === 'ss_chopper')!;
      const grounder = HIT_PRESETS.find((p) => p.id === '1b_grounder')!;

      assert.ok(chopper.distance < 140, `ss_chopper distance ${chopper.distance} should be < 140 ft`);
      assert.ok(grounder.distance < 100, `1b_grounder distance ${grounder.distance} should be < 100 ft`);
    });

    it('verifies 104 mph line drive missile transit speed and initial exit velocity', () => {
      const lineDrive = HIT_PRESETS.find((p) => p.id === 'line_drive_gap')!;
      const dt = lineDrive.hangTime / (lineDrive.samples.length - 1);
      const ds = Math.hypot(
        lineDrive.samples[1][0] - lineDrive.samples[0][0],
        lineDrive.samples[1][1] - lineDrive.samples[0][1],
      );
      const initialSpeedFps = ds / dt;

      // 104 mph * cos(16°) ~ 146 ft/s => assert >= 140 ft/s (> 95 mph)
      assert.ok(
        initialSpeedFps >= 140,
        `Initial velocity ${initialSpeedFps.toFixed(1)} ft/s should be >= 140 ft/s`,
      );

      // Verify time to reach 200 ft is <= 1.65s
      let transitTime200Ft = lineDrive.hangTime;
      for (let i = 0; i < lineDrive.samples.length - 1; i++) {
        const dCurrent = Math.hypot(lineDrive.samples[i][0], lineDrive.samples[i][1]);
        const dNext = Math.hypot(lineDrive.samples[i + 1][0], lineDrive.samples[i + 1][1]);
        if (dNext >= 200) {
          const frac = (200 - dCurrent) / (dNext - dCurrent);
          transitTime200Ft = (i + frac) * dt;
          break;
        }
      }

      assert.ok(
        transitTime200Ft <= 1.65,
        `104 mph line drive 200-ft transit time ${transitTime200Ft.toFixed(3)}s exceeds 1.65s`,
      );
    });

    it('verifies 106 mph moonshot carries >= 400 ft with apex >= 100 ft', () => {
      const moonshot = HIT_PRESETS.find((p) => p.id === 'moonshot_hr')!;
      assert.ok(moonshot.distance >= 400, `Moonshot distance ${moonshot.distance} should be >= 400 ft`);
      assert.ok(moonshot.apexHeight >= 100, `Moonshot apex ${moonshot.apexHeight} should be >= 100 ft`);
    });
  });

  describe('Parity with Canonical ball_flight.py Physics Engine', () => {
    it('matches exact canonical values for all 5 presets', () => {
      const chopper = HIT_PRESETS.find((p) => p.id === 'ss_chopper')!;
      assert.equal(chopper.hangTime, 1.32);
      assert.equal(chopper.apexHeight, 3.0);
      assert.equal(chopper.distance, 115.0);
      assert.deepEqual(chopper.landingPos, [-38.2, 0, -108.5]);

      const grounder = HIT_PRESETS.find((p) => p.id === '1b_grounder')!;
      assert.equal(grounder.hangTime, 0.664);
      assert.equal(grounder.apexHeight, 3.0);
      assert.equal(grounder.distance, 83.8);
      assert.deepEqual(grounder.landingPos, [58.4, 0, -60.1]);

      const lineDrive = HIT_PRESETS.find((p) => p.id === 'line_drive_gap')!;
      assert.equal(lineDrive.hangTime, 2.683);
      assert.equal(lineDrive.apexHeight, 30.5);
      assert.equal(lineDrive.distance, 304.4);
      assert.deepEqual(lineDrive.landingPos, [-83.9, 0, -292.7]);

      const flyBall = HIT_PRESETS.find((p) => p.id === 'fly_ball_rf')!;
      assert.equal(flyBall.hangTime, 4.386);
      assert.equal(flyBall.apexHeight, 79.0);
      assert.equal(flyBall.distance, 326.9);
      assert.deepEqual(flyBall.landingPos, [133.0, 0, -298.7]);

      const moonshot = HIT_PRESETS.find((p) => p.id === 'moonshot_hr')!;
      assert.equal(moonshot.hangTime, 5.157);
      assert.equal(moonshot.apexHeight, 108.5);
      assert.equal(moonshot.distance, 424.2);
      assert.deepEqual(moonshot.landingPos, [0.0, 0, -424.2]);
    });

    it('guarantees strictly monotonic 2D distance across all grounder samples', () => {
      const grounderPresets = HIT_PRESETS.filter((p) => p.isGrounder);
      assert.ok(grounderPresets.length >= 2);

      for (const preset of grounderPresets) {
        let prevDistance = -1;
        for (let i = 0; i < preset.samples.length; i++) {
          const sample = preset.samples[i];
          const dist = Math.hypot(sample[0], sample[1]);
          assert.ok(
            dist >= prevDistance - 1e-4,
            `Sample ${i} in ${preset.id} distance ${dist} moved backwards from ${prevDistance}`,
          );
          assert.ok(
            sample[2] >= 0.0,
            `Sample ${i} in ${preset.id} has negative height ${sample[2]}`,
          );
          prevDistance = dist;
        }
      }
    });

    it('matches trajectory generated dynamically via computeBattedBallTrajectory', () => {
      const traj = computeBattedBallTrajectory(95.0, 2.0, 32.0);
      assert.equal(traj.exitVelocityMph, 95.0);
      assert.equal(traj.launchAngleDeg, 2.0);
      assert.equal(traj.sprayAngleDeg, 32.0);
      assert.equal(traj.hangTime, 6.158);
      assert.equal(traj.distance, 319.7);
      assert.deepEqual(traj.landingPos, [169.4, 0, -271.1]);
      assert.equal(traj.samples.length, 20);
    });
  });
});
