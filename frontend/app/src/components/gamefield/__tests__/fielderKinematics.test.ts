import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  statcastToScene,
  computeFielderPursuit,
  computeAllFielderPositions,
  getCatchVisualProfile,
} from '../fielderKinematics';

describe('Fielder Pursuit Kinematics', () => {
  it('converts Statcast coordinates to Three.js scene coordinates', () => {
    // Statcast +X is right field, +Y is depth toward CF, +Z is height
    // Three.js X is +X, Y is +Z, Z is -Y
    const scenePos = statcastToScene(-115.0, 255.0, 0.0);
    assert.deepEqual(scenePos, [-115.0, 0.0, -255.0]);

    const elevated = statcastToScene(0.0, 320.0, 6.5);
    assert.deepEqual(elevated, [0.0, 6.5, -320.0]);
  });

  it('holds pre-pitch position during reaction delay beat', () => {
    // Fielder breaks after 0.25s reaction time
    const pursuit = computeFielderPursuit({
      startStatcast: [0.0, 330.0],
      targetStatcast: [20.0, 300.0, 3.0],
      elapsedTime: 0.15,
      totalDuration: 3.5,
      reactionDelay: 0.25,
    });

    assert.equal(pursuit.hasBroken, false);
    assert.deepEqual(pursuit.currentScenePos, [0.0, 0.0, -330.0]);
    assert.equal(pursuit.progress, 0.0);
  });

  it('smoothly interpolates scene position during sprint pursuit', () => {
    // Fielder sprints from (0, 330) to (20, 300) between t=0.25 and t=3.25
    const pursuit = computeFielderPursuit({
      startStatcast: [0.0, 330.0],
      targetStatcast: [20.0, 300.0, 0.0],
      elapsedTime: 1.75, // Halfway through sprint (1.5s into 3.0s sprint)
      totalDuration: 3.25,
      reactionDelay: 0.25,
    });

    assert.equal(pursuit.hasBroken, true);
    assert.equal(pursuit.isArrived, false);
    assert.ok(Math.abs(pursuit.progress - 0.5) < 1e-3);
    // Position should be midpoint: X=10, Z=-315
    assert.ok(Math.abs(pursuit.currentScenePos[0] - 10.0) < 0.1);
    assert.ok(Math.abs(pursuit.currentScenePos[2] - (-315.0)) < 0.1);
    // Base mesh stays at turf level (Y = 0)
    assert.equal(pursuit.currentScenePos[1], 0.0);
  });

  it('locks exactly at target intercept coordinate upon arrival', () => {
    const pursuit = computeFielderPursuit({
      startStatcast: [-45.0, 115.0],
      targetStatcast: [-55.0, 105.0, 0.0],
      elapsedTime: 2.5,
      totalDuration: 2.0,
      reactionDelay: 0.25,
    });

    assert.equal(pursuit.isArrived, true);
    assert.equal(pursuit.progress, 1.0);
    assert.deepEqual(pursuit.currentScenePos, [-55.0, 0.0, -105.0]);
  });

  it('safely handles short hang times without division by zero', () => {
    // Rocket line drive arrives in 0.20s (< 0.25s default reaction)
    const pursuit = computeFielderPursuit({
      startStatcast: [-63.6, 63.6],
      targetStatcast: [-65.0, 64.0, 2.5],
      elapsedTime: 0.20,
      totalDuration: 0.20,
      reactionDelay: 0.25,
    });

    assert.equal(pursuit.isArrived, true);
    assert.equal(pursuit.progress, 1.0);
    assert.deepEqual(pursuit.currentScenePos, [-65.0, 0.0, -64.0]);
    assert.deepEqual(pursuit.gloveScenePos, [-65.0, 2.5, -64.0]);
  });

  it('computes heading angle facing sprint direction with standstill guard', () => {
    // Sprints toward positive X and toward home plate (positive scene Z)
    const moving = computeFielderPursuit({
      startStatcast: [0.0, 330.0],
      targetStatcast: [20.0, 300.0, 0.0],
      elapsedTime: 1.0,
      totalDuration: 3.0,
    });
    // deltaX = 20, deltaZ = -(300 - 330) = +30 -> atan2(20, 30) ≈ 0.588 rad
    assert.ok(Math.abs(moving.headingAngle - Math.atan2(20, 30)) < 1e-4);

    // Standstill at start position holds heading 0 without NaN
    const stationary = computeFielderPursuit({
      startStatcast: [0.0, 330.0],
      targetStatcast: [0.0, 330.0, 0.0],
      elapsedTime: 1.0,
      totalDuration: 3.0,
    });
    assert.equal(stationary.headingAngle, 0.0);
    assert.equal(Number.isNaN(stationary.headingAngle), false);
  });

  it('maps fielding types to distinct catch visual profiles', () => {
    const wallLeap = getCatchVisualProfile('WALL_LEAP');
    assert.equal(wallLeap.badgeLabel, 'WALL LEAP');
    assert.equal(wallLeap.ringColor, '#EF4444');
    assert.equal(wallLeap.isCaught, true);

    const sliding = getCatchVisualProfile('SLIDING_CATCH');
    assert.equal(sliding.badgeLabel, 'SLIDING CATCH');
    assert.equal(sliding.ringColor, '#F59E0B');
    assert.equal(sliding.isCaught, true);

    const scoop = getCatchVisualProfile('GROUND_SCOOP');
    assert.equal(scoop.badgeLabel, 'FIELDED');
    assert.equal(scoop.ringColor, '#3B82F6');
    assert.equal(scoop.isCaught, true);

    const routine = getCatchVisualProfile('ROUTINE_FLY_CATCH');
    assert.equal(routine.ringColor, '#10B981');
    assert.equal(routine.isCaught, true);

    const unfielded = getCatchVisualProfile('UNFIELDED');
    assert.equal(unfielded.isCaught, false);
    assert.equal(unfielded.showRing, false);

    const homerun = getCatchVisualProfile('HOME_RUN');
    assert.equal(homerun.isCaught, false);

    const foul = getCatchVisualProfile('FOUL');
    assert.equal(foul.isCaught, false);
  });

  it('updates all 8 fielders with off-ball shading when one fielder pursues', () => {
    const allFielders = computeAllFielderPositions({
      activeFielderId: 'CF',
      activeStartStatcast: [0.0, 330.0],
      activeTargetStatcast: [-40.0, 290.0, 2.0],
      elapsedTime: 2.0,
      totalDuration: 3.0,
    });

    assert.equal(allFielders.size, 8);
    // CF is actively moving
    const cf = allFielders.get('CF');
    assert.ok(cf);
    assert.notDeepEqual(cf.scenePos, [0.0, 0.0, -330.0]);

    // LF shades slightly toward the ball to back up
    const lf = allFielders.get('LF');
    assert.ok(lf);
    assert.ok(lf.scenePos[0] > -115.0); // LF stepped toward center
  });
});

