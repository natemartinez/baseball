import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';

import {
  BASE_1B_POS,
  BASE_2B_POS,
  BASE_3B_POS,
  FOUL_POLE_HEIGHT,
  HOME_PLATE_CIRCLE_POS,
  HOME_PLATE_CIRCLE_RADIUS,
  HOME_PLATE_DEPTH,
  HOME_PLATE_HALF_WIDTH,
  createOutfieldWallCapGeometry,
  createOutfieldWallGeometry,
  warningTrackShape,
} from '../fieldGeometry';
import {
  FOUL_POLE_GOLD,
  FieldScene,
  WALL_COLOR,
  WALL_TRIM_COLOR,
} from '../FieldScene';
import { FoulPoles, FOUL_POLE_COLOR } from '../FoulPoles';
import {
  WallDistanceMarkers,
  WALL_DISTANCE_MARKERS,
} from '../WallDistanceMarkers';

describe('FieldScene Outfield Wall & Warning Track Integration', () => {
  it('exports wall and warning track geometry instances without runtime errors', () => {
    const wallGeom = createOutfieldWallGeometry();
    const capGeom = createOutfieldWallCapGeometry();
    assert.ok(wallGeom instanceof THREE.BufferGeometry);
    assert.ok(capGeom instanceof THREE.BufferGeometry);
    assert.ok(warningTrackShape instanceof THREE.Shape);

    // Verify geometries contain valid vertex and index buffers
    assert.ok((wallGeom.getAttribute('position')?.count ?? 0) > 0);
    assert.ok((capGeom.getAttribute('position')?.count ?? 0) > 0);
    assert.ok((wallGeom.getIndex()?.count ?? 0) > 0);
    assert.ok((capGeom.getIndex()?.count ?? 0) > 0);
  });

  it('preserves plate projection and base positions unchanged', () => {
    assert.equal(HOME_PLATE_HALF_WIDTH, 17 / 12 / 2);
    assert.equal(HOME_PLATE_DEPTH, 17 / 12);
    assert.deepEqual(BASE_1B_POS, [63.64, 0.1, -63.64]);
    assert.deepEqual(BASE_2B_POS, [0, 0.1, -127.28]);
    assert.deepEqual(BASE_3B_POS, [-63.64, 0.1, -63.64]);
    assert.deepEqual(HOME_PLATE_CIRCLE_POS, [0, 0.02, 0]);
    assert.equal(HOME_PLATE_CIRCLE_RADIUS, 13.0);
  });

  it('exports FieldScene component and local outfield theme constants mirroring colors.field', () => {
    assert.equal(typeof FieldScene, 'function');
    assert.equal(WALL_COLOR, '#12212C');
    assert.equal(WALL_TRIM_COLOR, '#1F3546');
    assert.equal(FOUL_POLE_GOLD, '#FFD700');
  });

  it('maintains foul pole specifications for integrated perimeter', () => {
    assert.equal(FOUL_POLE_COLOR, '#FFD700');
    assert.equal(FOUL_POLE_HEIGHT, 32.0);
    const element = FoulPoles();
    assert.ok(element, 'FoulPoles element must be instantiated cleanly');
  });

  it('ensures clean geometry disposal for memory management', () => {
    const wall = createOutfieldWallGeometry();
    const cap = createOutfieldWallCapGeometry();
    assert.doesNotThrow(() => {
      wall.dispose();
      cap.dispose();
    });
  });

  it('integrates wall distance markers on fence perimeter', () => {
    assert.equal(WALL_DISTANCE_MARKERS.length, 5);
    const element = WallDistanceMarkers();
    assert.ok(element, 'WallDistanceMarkers element must be instantiated cleanly');
    assert.equal(element.type, 'group');
  });
});
