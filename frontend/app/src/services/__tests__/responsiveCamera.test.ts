import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  BASE_ASPECT,
  BIRDSEYE_SHOT,
  GROUNDER_SHOT,
  LINE_DRIVE_SHOT,
  FLY_BALL_SHOT,
  PITCH_SHOT,
  computeAdaptiveBattedBallShot,
  computeBroadcastTrackingPose,
  computeGrounderShot,
  computeIsometricFollowPose,
  getResponsiveCameraShot,
  resolveGameCameraMode,
  sampleBallGroundTrajectory,
  sampleBallScenePosition,
} from '../../components/camera/cameraShots.ts';

describe('Responsive Camera Shot Director', () => {
  describe('Widescreen viewports (>= 16:9)', () => {
    it('returns exact base PITCH_SHOT for 16:9 widescreen', () => {
      const shot = getResponsiveCameraShot('PITCH', 16 / 9);
      assert.deepEqual(shot.position, PITCH_SHOT.position);
      assert.deepEqual(shot.target, PITCH_SHOT.target);
      assert.equal(shot.fov, PITCH_SHOT.fov);
    });

    it('returns exact base BIRDSEYE_SHOT for 16:9 widescreen', () => {
      const shot = getResponsiveCameraShot('BIRDSEYE', 16 / 9);
      assert.deepEqual(shot.position, BIRDSEYE_SHOT.position);
      assert.deepEqual(shot.target, BIRDSEYE_SHOT.target);
      assert.equal(shot.fov, BIRDSEYE_SHOT.fov);
    });

    it('returns responsive GROUNDER shot for 16:9 widescreen based on GROUNDER_SHOT', () => {
      const shot = getResponsiveCameraShot('GROUNDER', 16 / 9);
      assert.equal(shot.position[1], GROUNDER_SHOT.position[1]);
      assert.equal(shot.position[2], GROUNDER_SHOT.position[2]);
      assert.equal(shot.fov, GROUNDER_SHOT.fov);
    });

    it('preserves base shots on ultrawide (21:9)', () => {
      const pitchShot = getResponsiveCameraShot('PITCH', 21 / 9);
      assert.deepEqual(pitchShot.position, PITCH_SHOT.position);
      assert.equal(pitchShot.fov, PITCH_SHOT.fov);

      const birdseyeShot = getResponsiveCameraShot('BIRDSEYE', 21 / 9);
      assert.deepEqual(birdseyeShot.position, BIRDSEYE_SHOT.position);
      assert.equal(birdseyeShot.fov, BIRDSEYE_SHOT.fov);
    });
  });

  describe('Narrow & Portrait viewports (< 16:9)', () => {
    it('dollies back PITCH_SHOT to keep batter boxes in frame on tablet (4:3)', () => {
      const shot = getResponsiveCameraShot('PITCH', 4 / 3);
      // Camera moves back in +Z to expand horizontal field at plate
      assert.ok(shot.position[2] > PITCH_SHOT.position[2]);
      // Slight rise in Y along view vector to preserve pitch angle
      assert.ok(shot.position[1] > PITCH_SHOT.position[1]);
      // Target remains locked on the mound
      assert.deepEqual(shot.target, PITCH_SHOT.target);
    });

    it('dollies back PITCH_SHOT further on mobile portrait (9:16) while keeping FOV natural', () => {
      const shot = getResponsiveCameraShot('PITCH', 9 / 16);
      assert.ok(shot.position[2] > 10.0);
      assert.ok(shot.fov <= 76.0); // No extreme fisheye distortion

      // Calculate horizontal half-span at home plate (z = 0)
      const halfFovRad = (shot.fov * Math.PI) / 360;
      const distToPlate = shot.position[2];
      const horizontalHalfWidth = distToPlate * (9 / 16) * Math.tan(halfFovRad);

      // Outer edge of batter's box is at x = ±5.21 ft. Must have > 5.5 ft horizontal span
      assert.ok(
        horizontalHalfWidth >= 5.5,
        `Expected horizontal span >= 5.5 ft, got ${horizontalHalfWidth}`,
      );
    });

    it('scales BIRDSEYE_SHOT height and adjusts target towards plate on mobile portrait', () => {
      const shot = getResponsiveCameraShot('BIRDSEYE', 9 / 16);
      // Scaled up in height (Y) and pulled back in Z
      assert.ok(shot.position[1] > BIRDSEYE_SHOT.position[1]);
      assert.ok(shot.position[2] > BIRDSEYE_SHOT.position[2]);
      // Target shifted slightly toward home plate to frame below top HUD
      assert.ok(shot.target[2] > BIRDSEYE_SHOT.target[2]);
    });
  });

  describe('Fallback and edge-case handling', () => {
    it('gracefully handles non-positive or non-finite aspect ratios', () => {
      const shotZero = getResponsiveCameraShot('PITCH', 0);
      assert.equal(shotZero.fov, PITCH_SHOT.fov);

      const shotNaN = getResponsiveCameraShot('BIRDSEYE', NaN);
      assert.equal(shotNaN.fov, BIRDSEYE_SHOT.fov);
    });
  });

  describe('computeBroadcastTrackingPose', () => {
    it('centers camera look-at on ball position', () => {
      const ball: [number, number, number] = [30, 0, -120];
      const pose = computeBroadcastTrackingPose(ball, 16 / 9);
      assert.ok(Math.abs(pose.target[0] - 30) < 0.1);
      assert.ok(Math.abs(pose.target[2] - (-120)) < 0.1);
      assert.equal(pose.fov, 34);
    });

    it('safely handles NaN or non-finite inputs by falling back to safe target', () => {
      const invalidBall: [number, number, number] = [NaN, 0, -Infinity];
      const pose = computeBroadcastTrackingPose(invalidBall, 16 / 9);
      assert.ok(Number.isFinite(pose.target[0]));
      assert.ok(Number.isFinite(pose.target[1]));
      assert.ok(Number.isFinite(pose.target[2]));
      assert.ok(Number.isFinite(pose.position[0]));
      assert.ok(Number.isFinite(pose.position[1]));
      assert.ok(Number.isFinite(pose.position[2]));
    });
  });

  describe('sampleBallScenePosition', () => {
    it('falls back safely for empty samples', () => {
      const pos = sampleBallScenePosition([], 0, 1.0);
      assert.deepEqual(pos, [0, 1.0, -40]);
    });

    it('translates physics coordinates (x, y, z) into scene coordinates (x, z, -y)', () => {
      // Physics: x=10, y=80, z=5 -> Scene: [10, 5, -80]
      const samples: [number, number, number][] = [[10, 80, 5]];
      const pos = sampleBallScenePosition(samples, 0, 1.0);
      assert.deepEqual(pos, [10, 5, -80]);
    });

    it('interpolates intermediate positions based on elapsed / hangTime', () => {
      const samples: [number, number, number][] = [
        [0, 0, 0],
        [20, 100, 10],
      ];
      // Halfway (elapsed = 1.0, hangTime = 2.0)
      const pos = sampleBallScenePosition(samples, 1.0, 2.0);
      assert.ok(Math.abs(pos[0] - 10) < 0.01);
      assert.ok(Math.abs(pos[1] - 5) < 0.01);
      assert.ok(Math.abs(pos[2] - (-50)) < 0.01);
    });

    it('clamps progress to 1.0 when elapsed exceeds hangTime', () => {
      const samples: [number, number, number][] = [
        [0, 0, 0],
        [20, 100, 10],
      ];
      const pos = sampleBallScenePosition(samples, 5.0, 2.0);
      assert.ok(Math.abs(pos[0] - 20) < 0.01);
      assert.ok(Math.abs(pos[1] - 10) < 0.01);
      assert.ok(Math.abs(pos[2] - (-100)) < 0.01);
    });

    it('safely handles NaN values in samples', () => {
      const samples: [number, number, number][] = [[NaN, 100, NaN]];
      const pos = sampleBallScenePosition(samples, 0, 1.0);
      assert.ok(Number.isFinite(pos[0]));
      assert.ok(Number.isFinite(pos[1]));
      assert.ok(Number.isFinite(pos[2]));
    });
  });

  describe('computeIsometricFollowPose', () => {
    it('computes 45-degree isometric position offset from leading target', () => {
      const ballPos: [number, number, number] = [0, 0, 0];
      const travelDir: [number, number, number] = [0, 0, -1]; // Toward center field
      const pose = computeIsometricFollowPose(ballPos, travelDir, 16 / 9);

      // Target leads 30 ft downfield: [0, 1.0, -30]
      assert.ok(Math.abs(pose.target[0] - 0) < 0.1);
      assert.ok(Math.abs(pose.target[1] - 1.0) < 0.1);
      assert.ok(Math.abs(pose.target[2] - (-30)) < 0.1);

      // Camera sits 90 ft up and 90 ft behind target: [0, 90, -30 + 90 = 60]
      assert.ok(Math.abs(pose.position[0] - 0) < 0.1);
      assert.ok(Math.abs(pose.position[1] - 90) < 0.1);
      assert.ok(Math.abs(pose.position[2] - 60) < 0.1);
      assert.equal(pose.fov, 38);
    });

    it('safely defaults to center field lead when travel direction is zero', () => {
      const ballPos: [number, number, number] = [20, 0, -80];
      const zeroDir: [number, number, number] = [0, 0, 0];
      const pose = computeIsometricFollowPose(ballPos, zeroDir, 16 / 9);

      assert.ok(Number.isFinite(pose.target[0]));
      assert.ok(Number.isFinite(pose.target[2]));
      assert.ok(pose.target[2] < -80); // Leads forward along -Z
    });

    it('safely handles NaN inputs with robust fallback', () => {
      const invalidBall: [number, number, number] = [NaN, 0, -Infinity];
      const invalidDir: [number, number, number] = [NaN, NaN, NaN];
      const pose = computeIsometricFollowPose(invalidBall, invalidDir, 16 / 9);

      assert.ok(Number.isFinite(pose.target[0]));
      assert.ok(Number.isFinite(pose.target[1]));
      assert.ok(Number.isFinite(pose.target[2]));
      assert.ok(Number.isFinite(pose.position[0]));
      assert.ok(Number.isFinite(pose.position[1]));
      assert.ok(Number.isFinite(pose.position[2]));
    });

    it('preserves close tactile altitude on portrait screens without pulling far back', () => {
      const ballPos: [number, number, number] = [0, 0, 0];
      const dir: [number, number, number] = [0, 0, -1];
      const widescreenPose = computeIsometricFollowPose(ballPos, dir, 16 / 9);
      const portraitPose = computeIsometricFollowPose(ballPos, dir, 9 / 16);

      // Altitude on portrait remains close and tactile (within 15% of base)
      assert.ok(portraitPose.position[1] >= widescreenPose.position[1]);
      assert.ok(portraitPose.position[1] <= widescreenPose.position[1] * 1.15);
    });
  });

  describe('computeAdaptiveBattedBallShot', () => {
    describe('Grounder & Chopper mode (isGrounder === true)', () => {
      it('anchors camera behind home plate and blends look-at target towards 1B bag', () => {
        // Grounder hit towards shortstop at (-35, 0, -80)
        const ballPos: [number, number, number] = [-35, 0, -80];
        const dir: [number, number, number] = [-0.4, 0, -0.9];
        const shot = computeAdaptiveBattedBallShot(
          ballPos,
          dir,
          10, // bounce height of 10 ft
          0.3,
          true, // isGrounder
          [ -35, 0, -100 ],
          16 / 9,
        );

        // Camera position sits behind home plate elevated at GROUNDER_SHOT preset
        assert.equal(shot.position[0], GROUNDER_SHOT.position[0]);
        assert.equal(shot.position[1], GROUNDER_SHOT.position[1]);
        assert.equal(shot.position[2], GROUNDER_SHOT.position[2]);

        // Target Y is strictly 1.0 (rock-steady horizon / bounce filtering)
        assert.equal(shot.target[1], 1.0);

        // Target X and Z are blended towards 1B bag (63.64, 0, -63.64)
        // w = 0.35: targetX = -35 * 0.65 + 63.64 * 0.35 = -22.75 + 22.27 = -0.48
        assert.ok(shot.target[0] > -35); // Blended rightward toward 1B
        assert.ok(shot.target[2] > -80); // Blended back toward 1B depth
        assert.equal(shot.fov, GROUNDER_SHOT.fov);
      });

      it('anchors GROUNDER camera station at GROUNDER_SHOT position and pans target', () => {
        const grounderShot = computeGrounderShot([-45, 0, -115], 16 / 9);

        // Position is anchored at home plate
        assert.equal(grounderShot.position[0], GROUNDER_SHOT.position[0]);
        assert.equal(grounderShot.position[1], GROUNDER_SHOT.position[1]);
        assert.equal(grounderShot.position[2], GROUNDER_SHOT.position[2]);

        // Target tracks ball towards shortstop/1B
        assert.ok(grounderShot.target[2] < -50);
      });
    });

    describe('Fly Ball & Line Drive mode (isGrounder === false)', () => {
      const landingPos: [number, number, number] = [40, 0, -280];

      it('elevates look-at target and applies dynamic telephoto zoom during flight', () => {
        const ballPos: [number, number, number] = [10, 0, -70];
        const dir: [number, number, number] = [0.2, 0, -0.98];
        const shot = computeAdaptiveBattedBallShot(
          ballPos,
          dir,
          60, // 60 ft height
          0.25, // early ascent
          false,
          landingPos,
          16 / 9,
        );

        // Elevated look-at target: 1.0 + 60 * 0.38 = 23.8
        assert.ok(Math.abs(shot.target[1] - 23.8) < 0.1);
        // Dynamic telephoto zoom: narrows FOV as ball travels out (<= 40.0)
        assert.ok(shot.fov <= 40.0 && shot.fov >= 18.0);
        // Focus anchor is centered around ball during early ascent
        assert.ok(shot.target[2] > -120);
      });

      it('smoothly glides tracking anchor toward landing zone during descent', () => {
        // Descent near landing zone: progress = 0.95, ball height descending to 5 ft
        const ballPos: [number, number, number] = [38, 0, -270];
        const dir: [number, number, number] = [0.2, 0, -0.98];
        const shot = computeAdaptiveBattedBallShot(
          ballPos,
          dir,
          5,
          0.95, // late descent
          false,
          landingPos,
          16 / 9,
        );

        // Look-at target has smoothly returned down to near-turf level
        assert.ok(shot.target[1] < 4.0);
        // Tracking anchor has converged (>95%) onto landingPos (40, 0, -280)
        assert.ok(Math.abs(shot.target[0] - 40) < 3.0);
        assert.ok(Math.abs(shot.target[2] - (-280)) < 15.0);
      });

      it('safely handles NaN and missing landingPos without breaking', () => {
        const shot = computeAdaptiveBattedBallShot(
          [NaN, NaN, NaN],
          [NaN, NaN, NaN],
          NaN,
          NaN,
          false,
          undefined,
          NaN,
        );

        assert.ok(Number.isFinite(shot.position[0]));
        assert.ok(Number.isFinite(shot.position[1]));
        assert.ok(Number.isFinite(shot.position[2]));
        assert.ok(Number.isFinite(shot.target[0]));
        assert.ok(Number.isFinite(shot.target[1]));
        assert.ok(Number.isFinite(shot.target[2]));
        assert.ok(Number.isFinite(shot.fov));
      });

      it('exports LINE_DRIVE_SHOT and FLY_BALL_SHOT presets conforming to CameraShot', () => {
        assert.equal(LINE_DRIVE_SHOT.position[0], 0);
        assert.equal(LINE_DRIVE_SHOT.position[1], 54.0);
        assert.equal(LINE_DRIVE_SHOT.position[2], 52.0);
        assert.deepEqual(LINE_DRIVE_SHOT.target, [0, 1.0, -100.0]);
        assert.equal(LINE_DRIVE_SHOT.fov, 40);

        assert.equal(FLY_BALL_SHOT.position[0], 0);
        assert.equal(FLY_BALL_SHOT.position[1], 85.0);
        assert.equal(FLY_BALL_SHOT.position[2], 68.0);
        assert.deepEqual(FLY_BALL_SHOT.target, [0, 1.0, -120.0]);
        assert.equal(FLY_BALL_SHOT.fov, 42);
      });

      it('keeps camera position anchored behind home plate (Z >= 50) during deep ball flight', () => {
        const deepOutfieldBall = computeAdaptiveBattedBallShot(
          [-80, 0, -280],
          [-0.27, 0, -0.96],
          25,
          0.6,
          false,
          [-90, 0, -320],
          16 / 9,
          18, // line drive
        );

        // Station stays anchored behind home plate at LINE_DRIVE_SHOT position
        assert.equal(deepOutfieldBall.position[0], LINE_DRIVE_SHOT.position[0]);
        assert.equal(deepOutfieldBall.position[1], LINE_DRIVE_SHOT.position[1]);
        assert.equal(deepOutfieldBall.position[2], LINE_DRIVE_SHOT.position[2]);

        // Look-at target pans deep into the gap to follow the ball
        assert.ok(deepOutfieldBall.target[2] < -200);
      });

      it('applies dynamic telephoto zoom (narrows FOV) as ball travels deep into the outfield', () => {
        // Near ball at contact (dist ~ 20 ft)
        const contactShot = computeAdaptiveBattedBallShot(
          [0, 0, -20],
          [0, 0, -1],
          5,
          0.05,
          false,
          [0, 0, -380],
          16 / 9,
          32, // fly ball
        );

        // Deep ball at warning track (dist ~ 350 ft)
        const deepShot = computeAdaptiveBattedBallShot(
          [0, 0, -350],
          [0, 0, -1],
          30,
          0.85,
          false,
          [0, 0, -380],
          16 / 9,
          32, // fly ball
        );

        // Near shot preserves full wide base FOV
        assert.equal(contactShot.fov, FLY_BALL_SHOT.fov);

        // Deep shot applies telephoto zoom (narrower FOV between 18° and 26°) to keep ball large
        assert.ok(deepShot.fov < contactShot.fov);
        assert.ok(deepShot.fov >= 18.0 && deepShot.fov <= 26.0);
      });

      it('adapts camera altitude and distance based on launchAngle (< 25 line drive vs >= 25 fly ball)', () => {
        const shotLineDrive = computeAdaptiveBattedBallShot(
          [0, 0, -50],
          [0, 0, -1],
          15,
          0.3,
          false,
          [0, 0, -200],
          16 / 9,
          16, // line drive launch angle
        );

        const shotFlyBall = computeAdaptiveBattedBallShot(
          [0, 0, -50],
          [0, 0, -1],
          15,
          0.3,
          false,
          [0, 0, -200],
          16 / 9,
          32, // fly ball launch angle
        );

        // Line drive camera is lower and closer than fly ball camera
        assert.ok(shotLineDrive.position[1] < shotFlyBall.position[1]);
        assert.ok(shotLineDrive.position[2] < shotFlyBall.position[2]);
        assert.equal(shotLineDrive.position[1], LINE_DRIVE_SHOT.position[1]);
        assert.equal(shotFlyBall.position[1], FLY_BALL_SHOT.position[1]);
      });

      it('respects custom baseShot override and defaults to FLY_BALL_SHOT when launchAngle is omitted', () => {
        const customShot = computeAdaptiveBattedBallShot(
          [0, 0, 0],
          [0, 0, 0],
          0,
          0,
          false,
          undefined,
          16 / 9,
          undefined,
          { position: [0, 50.0, 60.0], target: [0, 1, -50], fov: 32 },
        );

        assert.equal(customShot.position[1], 50.0);
        assert.equal(customShot.position[2], 60.0);
        assert.equal(customShot.fov, 32);

        const defaultShot = computeAdaptiveBattedBallShot(
          [0, 0, 0],
          [0, 0, 0],
          0,
          0,
          false,
          undefined,
          16 / 9,
        );

        assert.equal(defaultShot.position[1], FLY_BALL_SHOT.position[1]);
        assert.equal(defaultShot.position[2], FLY_BALL_SHOT.position[2]);
        assert.equal(defaultShot.fov, FLY_BALL_SHOT.fov);
      });
    });
  });

  describe('sampleBallGroundTrajectory', () => {
    it('extracts ground position, travel direction, and ballHeight', () => {
      // 2-sample trajectory: from (0, 0, 0) to (30, 120, 50) in physics coords
      const samples: [number, number, number][] = [
        [0, 0, 0],
        [30, 120, 50],
      ];
      const result = sampleBallGroundTrajectory(samples, 0.5, 1.0);

      // Ground position Y must be 0 (isolated ground plane)
      assert.equal(result.groundPos[1], 0);
      assert.ok(Math.abs(result.groundPos[0] - 15) < 0.1);
      assert.ok(Math.abs(result.groundPos[2] - (-60)) < 0.1);
      assert.equal(result.ballHeight, 25); // Interpolated height (50 * 0.5)

      // Travel direction must be normalized pointing toward (+30, 0, -120)
      const len = Math.hypot(result.travelDirection[0], result.travelDirection[2]);
      assert.ok(Math.abs(len - 1.0) < 0.01);
      assert.ok(result.travelDirection[0] > 0);
      assert.ok(result.travelDirection[2] < 0);
    });

    it('safely handles empty or single samples with ballHeight fallback', () => {
      const emptyResult = sampleBallGroundTrajectory([], 0, 1.0);
      assert.deepEqual(emptyResult.groundPos, [0, 0, -40]);
      assert.deepEqual(emptyResult.travelDirection, [0, 0, -1]);
      assert.equal(emptyResult.ballHeight, 0);

      const singleResult = sampleBallGroundTrajectory([[10, 50, 15]], 0, 1.0);
      assert.deepEqual(singleResult.groundPos, [10, 0, -50]);
      assert.deepEqual(singleResult.travelDirection, [0, 0, -1]);
      assert.equal(singleResult.ballHeight, 15);
    });
  });

  describe('resolveGameCameraMode', () => {
    it('keeps PITCH camera during REACTING contact beat so contact is seen in batting view', () => {
      const mode = resolveGameCameraMode('REACTING', false, false, 'PITCH');
      assert.equal(mode, 'PITCH');
    });

    it('switches to TRACKING once in BATTED_BALL with active ball data', () => {
      const mode = resolveGameCameraMode('BATTED_BALL', true, false, 'PITCH');
      assert.equal(mode, 'TRACKING');
    });

    it('switches to GROUNDER once in BATTED_BALL when isGrounder is true', () => {
      const mode = resolveGameCameraMode('BATTED_BALL', true, false, 'PITCH', undefined, true);
      assert.equal(mode, 'GROUNDER');
    });

    it('holds TRACKING during IDLE resultCameraHold', () => {
      const mode = resolveGameCameraMode('IDLE', true, true, 'PITCH');
      assert.equal(mode, 'TRACKING');
    });

    it('snaps back to manualMode once resultCameraHold expires', () => {
      const mode = resolveGameCameraMode('IDLE', false, false, 'PITCH');
      assert.equal(mode, 'PITCH');
    });

    it('respects manual BIRDSEYE mode when no batted ball is active', () => {
      const mode = resolveGameCameraMode('IDLE', false, false, 'BIRDSEYE');
      assert.equal(mode, 'BIRDSEYE');
    });
  });
});

