import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';

import {
  BASE_1B_POS,
  BASE_3B_POS,
  BATTERS_BOX_LEFT_POS,
  BATTERS_BOX_RIGHT_POS,
  FOUL_LINE_LEFT_POS,
  FOUL_LINE_LEFT_ROTATION,
  FOUL_LINE_LENGTH,
  FOUL_LINE_RIGHT_POS,
  FOUL_LINE_RIGHT_ROTATION,
  HOME_PLATE_CIRCLE_POS,
  HOME_PLATE_CIRCLE_RADIUS,
  homePlateShape,
  infieldGrassShape,
} from '../fieldGeometry.ts';

describe('Field Geometry Baserunning / Foul Line Alignment', () => {
  const boxLength = 6.0;

  it('aligns right line near endpoint with top-middle of right batter box', () => {
    // Top-middle of right batter's box (z = center_z - length / 2)
    const expectedStartX = BATTERS_BOX_RIGHT_POS[0];
    const expectedStartZ = BATTERS_BOX_RIGHT_POS[2] - boxLength / 2;

    assert.equal(expectedStartX, 3.21);
    assert.equal(expectedStartZ, -3.71);

    // Compute near endpoint (local Z = +length / 2) rotated by FOUL_LINE_RIGHT_ROTATION
    const halfL = FOUL_LINE_LENGTH / 2;
    const rotY = FOUL_LINE_RIGHT_ROTATION[1];
    const nearX = FOUL_LINE_RIGHT_POS[0] + halfL * Math.sin(rotY);
    const nearZ = FOUL_LINE_RIGHT_POS[2] + halfL * Math.cos(rotY);

    assert.ok(
      Math.abs(nearX - expectedStartX) < 1e-4,
      `Expected nearX close to ${expectedStartX}, got ${nearX}`,
    );
    assert.ok(
      Math.abs(nearZ - expectedStartZ) < 1e-4,
      `Expected nearZ close to ${expectedStartZ}, got ${nearZ}`,
    );
  });

  it('aligns left line near endpoint with top-middle of left batter box', () => {
    // Top-middle of left batter's box
    const expectedStartX = BATTERS_BOX_LEFT_POS[0];
    const expectedStartZ = BATTERS_BOX_LEFT_POS[2] - boxLength / 2;

    assert.equal(expectedStartX, -3.21);
    assert.equal(expectedStartZ, -3.71);

    const halfL = FOUL_LINE_LENGTH / 2;
    const rotY = FOUL_LINE_LEFT_ROTATION[1];
    const nearX = FOUL_LINE_LEFT_POS[0] + halfL * Math.sin(rotY);
    const nearZ = FOUL_LINE_LEFT_POS[2] + halfL * Math.cos(rotY);

    assert.ok(
      Math.abs(nearX - expectedStartX) < 1e-4,
      `Expected nearX close to ${expectedStartX}, got ${nearX}`,
    );
    assert.ok(
      Math.abs(nearZ - expectedStartZ) < 1e-4,
      `Expected nearZ close to ${expectedStartZ}, got ${nearZ}`,
    );
  });

  it('does not meet at the bottom of home plate (0, 0, 0)', () => {
    const halfL = FOUL_LINE_LENGTH / 2;
    const rightNear = new THREE.Vector3(
      FOUL_LINE_RIGHT_POS[0] + halfL * Math.sin(FOUL_LINE_RIGHT_ROTATION[1]),
      FOUL_LINE_RIGHT_POS[1],
      FOUL_LINE_RIGHT_POS[2] + halfL * Math.cos(FOUL_LINE_RIGHT_ROTATION[1]),
    );
    const leftNear = new THREE.Vector3(
      FOUL_LINE_LEFT_POS[0] + halfL * Math.sin(FOUL_LINE_LEFT_ROTATION[1]),
      FOUL_LINE_LEFT_POS[1],
      FOUL_LINE_LEFT_POS[2] + halfL * Math.cos(FOUL_LINE_LEFT_ROTATION[1]),
    );

    // Distance to bottom of home plate (0, 0, 0)
    assert.ok(rightNear.length() > 4.0, 'Right line near endpoint should not be at (0, 0, 0)');
    assert.ok(leftNear.length() > 4.0, 'Left line near endpoint should not be at (0, 0, 0)');
    // Lines do not meet each other
    assert.ok(rightNear.distanceTo(leftNear) > 6.0, 'Lines should not meet each other');
  });

  it('passes directly through 1st base and 3rd base', () => {
    // Vector from start to 1B
    const startX = BATTERS_BOX_RIGHT_POS[0];
    const startZ = BATTERS_BOX_RIGHT_POS[2] - boxLength / 2;
    const dx = BASE_1B_POS[0] - startX;
    const dz = BASE_1B_POS[2] - startZ;
    const angle = Math.atan2(dx, -dz);

    assert.ok(
      Math.abs(-angle - FOUL_LINE_RIGHT_ROTATION[1]) < 1e-4,
      'Right foul line angle must match line to 1st base',
    );
    assert.ok(
      Math.abs(angle - FOUL_LINE_LEFT_ROTATION[1]) < 1e-4,
      'Left foul line angle must match line to 3rd base',
    );
  });

  describe('Home Plate Sand Circle', () => {
    const boxWidth = 4.0;
    const boxLength = 6.0;

    it('has standard 13-ft radius (26-ft diameter) centered at home plate apex', () => {
      assert.equal(HOME_PLATE_CIRCLE_RADIUS, 13.0);
      assert.deepEqual(HOME_PLATE_CIRCLE_POS, [0, 0.006, 0]);
    });

    it('fully holds home plate within the sand circle', () => {
      // Extract home plate 2D points from homePlateShape
      const points = homePlateShape.getPoints();
      assert.ok(points.length > 0, 'Home plate shape should have vertices');

      for (const pt of points) {
        // In Three.js shape space (x, y), world distance to center is hypot(pt.x, pt.y)
        const dist = Math.hypot(pt.x, pt.y);
        assert.ok(
          dist < HOME_PLATE_CIRCLE_RADIUS,
          `Home plate point (${pt.x}, ${pt.y}) dist ${dist} must be strictly inside circle radius ${HOME_PLATE_CIRCLE_RADIUS}`,
        );
      }
    });

    it('fully holds both batter boxes within the sand circle', () => {
      const boxes = [
        { name: 'Right', pos: BATTERS_BOX_RIGHT_POS },
        { name: 'Left', pos: BATTERS_BOX_LEFT_POS },
      ];

      for (const box of boxes) {
        const corners = [
          [box.pos[0] - boxWidth / 2, box.pos[2] - boxLength / 2],
          [box.pos[0] + boxWidth / 2, box.pos[2] - boxLength / 2],
          [box.pos[0] + boxWidth / 2, box.pos[2] + boxLength / 2],
          [box.pos[0] - boxWidth / 2, box.pos[2] + boxLength / 2],
        ];

        for (const [cx, cz] of corners) {
          const dist = Math.hypot(cx, cz);
          assert.ok(
            dist < HOME_PLATE_CIRCLE_RADIUS,
            `${box.name} batter box corner (${cx}, ${cz}) dist ${dist} must be inside circle radius ${HOME_PLATE_CIRCLE_RADIUS}`,
          );
        }
      }
    });

    it('infield grass diamond arcs around the sand circle without overlapping', () => {
      const geom = new THREE.ShapeGeometry(infieldGrassShape);
      geom.computeBoundingBox();
      const bbox = geom.boundingBox;

      assert.ok(bbox, 'Infield grass diamond must have a valid bounding box');
      // In shape space, Y = -Z. The circle top reaches Y = HOME_PLATE_CIRCLE_RADIUS (Z = -13).
      // The grass diamond minimum Y should be close to the circle arc intersection (~9.35) and never reach home plate (Y = 0)
      assert.ok(
        bbox.min.y >= HOME_PLATE_CIRCLE_RADIUS * Math.sin(Math.atan2(63.64, 61.5)) - 0.1,
        `Grass diamond min Y (${bbox.min.y}) must stay outside home plate circle`,
      );
      assert.ok(bbox.min.y > 0, 'Grass diamond should not cover home plate (y = 0)');
    });
  });
});
