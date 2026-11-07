import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  BASE_ASPECT,
  BIRDSEYE_SHOT,
  PITCH_SHOT,
  getResponsiveCameraShot,
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
});

