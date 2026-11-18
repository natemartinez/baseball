import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';

import {
  BASE_1B_POS,
  BASE_2B_POS,
  BASE_3B_POS,
  BATTERS_BOX_LEFT_POS,
  BATTERS_BOX_RIGHT_POS,
  FENCE_CENTER_DISTANCE,
  FENCE_FOUL_LINE_DISTANCE,
  FENCE_TOP_RAIL_HEIGHT,
  FENCE_WALL_HEIGHT,
  FENCE_WALL_THICKNESS,
  FOUL_LINE_LEFT_POS,
  FOUL_LINE_LEFT_ROTATION,
  FOUL_LINE_LENGTH,
  FOUL_LINE_RIGHT_POS,
  FOUL_LINE_RIGHT_ROTATION,
  FOUL_POLE_HEIGHT,
  FOUL_POLE_LEFT_POS,
  FOUL_POLE_RADIUS,
  FOUL_POLE_RIGHT_POS,
  HOME_PLATE_CIRCLE_POS,
  HOME_PLATE_CIRCLE_RADIUS,
  WARNING_TRACK_WIDTH,
  createOutfieldWallCapGeometry,
  createOutfieldWallGeometry,
  dirtSkirtShape,
  fenceDistance,
  getFencePoint,
  homePlateShape,
  infieldGrassShape,
  shapeY,
  warningTrackShape,
} from '../fieldGeometry.ts';

function pointInPolygon(pt: { x: number; y: number }, poly: { x: number; y: number }[]): boolean {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const xi = poly[i].x, yi = poly[i].y;
    const xj = poly[j].x, yj = poly[j].y;
    const intersect = ((yi > pt.y) !== (yj > pt.y)) &&
      (pt.x < ((xj - xi) * (pt.y - yi)) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

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
      assert.deepEqual(HOME_PLATE_CIRCLE_POS, [0, 0.020, 0]);
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

  describe('Infield Dirt Skirt (dirtSkirtShape)', () => {
    it('encompasses 1st base, 3rd base, and foul lines past the bags', () => {
      const pointsToCheck = [
        [63.64, -63.64],   // 1B
        [-63.64, -63.64],  // 3B
        [80.0, -80.0],     // Past 1B on foul line
        [-80.0, -80.0],    // Past 3B on foul line
        [0.0, -145.0],     // Deep 2B dirt behind bag
      ];

      const shapePoints = dirtSkirtShape.getPoints();
      for (const [x, z] of pointsToCheck) {
        const sy = -z;
        const isInside = pointInPolygon({ x, y: sy }, shapePoints);
        assert.ok(isInside, `Point (${x}, ${z}) should be inside dirtSkirtShape`);
      }
    });

    it('reaches the outer foul dirt boundary at left and right edges', () => {
      const shapePoints = dirtSkirtShape.getPoints();
      const maxX = Math.max(...shapePoints.map((p) => p.x));
      const minX = Math.min(...shapePoints.map((p) => p.x));

      assert.ok(maxX >= 90.0, `Expected maxX >= 90.0, got ${maxX}`);
      assert.ok(minX <= -90.0, `Expected minX <= -90.0, got ${minX}`);
    });
  });

  describe('Infield Grass Diamond (infieldGrassShape)', () => {
    it('leaves 1B, 2B, and 3B bags and sliding pits exposed on dirt', () => {
      const grassPoints = infieldGrassShape.getPoints();
      const slidingPitPoints = [
        [BASE_1B_POS[0], BASE_1B_POS[2]],                     // 1B bag
        [BASE_1B_POS[0] - 5.0, BASE_1B_POS[2]],               // 5ft inside 1B sliding pit
        [BASE_2B_POS[0], BASE_2B_POS[2]],                     // 2B bag
        [BASE_2B_POS[0], BASE_2B_POS[2] + 5.0],               // 5ft in front of 2B sliding pit
        [BASE_3B_POS[0], BASE_3B_POS[2]],                     // 3B bag
        [BASE_3B_POS[0] + 5.0, BASE_3B_POS[2]],               // 5ft inside 3B sliding pit
      ];

      for (const [bx, bz] of slidingPitPoints) {
        const isInside = pointInPolygon({ x: bx, y: -bz }, grassPoints);
        assert.equal(isInside, false, `Point at (${bx}, ${bz}) must be exposed in dirt cutout, not grass`);
      }
    });

    it('provides running lane dirt setback between home circle and 1B/3B', () => {
      const grassPoints = infieldGrassShape.getPoints();
      // Test points on the foul line (x=31.82, z=-31.82) and 2ft into fair territory (x=30.41, z=-33.23)
      const isFoulLineCovered = pointInPolygon({ x: 31.82, y: 31.82 }, grassPoints);
      assert.equal(isFoulLineCovered, false, 'Baseline foul line must be exposed dirt running lane');

      const isFairRunningLaneCovered = pointInPolygon({ x: 30.41, y: 33.23 }, grassPoints);
      assert.equal(isFairRunningLaneCovered, false, 'Fair territory running lane must be exposed dirt');
    });
  });

  describe('Outfield Fence Dimensions & Foul Line Extension', () => {
    it('exports accurate regulation fence distance constants matching backend', () => {
      assert.equal(FENCE_CENTER_DISTANCE, 400.0);
      assert.equal(FENCE_FOUL_LINE_DISTANCE, 330.0);
      assert.equal(FENCE_WALL_HEIGHT, 8.0);
      assert.equal(WARNING_TRACK_WIDTH, 15.0);
      assert.equal(FENCE_WALL_THICKNESS, 1.0);
      assert.equal(FENCE_TOP_RAIL_HEIGHT, 0.5);
      assert.equal(FOUL_POLE_HEIGHT, 32.0);
      assert.equal(FOUL_POLE_RADIUS, 0.4);
    });

    it('computes fence distances matching backend formula', () => {
      assert.equal(fenceDistance(0), 400.0); // Center Field
      assert.equal(fenceDistance(45), 330.0); // Right Field Line
      assert.equal(fenceDistance(-45), 330.0); // Left Field Line
      assert.equal(fenceDistance(22.5), 365.0); // Right-Center Gap
      assert.equal(fenceDistance(-22.5), 365.0); // Left-Center Gap
    });

    it('computes 3D fence points with optional radial offset', () => {
      const cf = getFencePoint(0);
      assert.ok(Math.abs(cf[0] - 0) < 1e-4);
      assert.equal(cf[1], 0);
      assert.ok(Math.abs(cf[2] - (-400.0)) < 1e-4);

      const cfOffset = getFencePoint(0, 1.0);
      assert.ok(Math.abs(cfOffset[2] - (-401.0)) < 1e-4);

      const rf = getFencePoint(45);
      const expectedRfX = 330.0 * Math.sin(Math.PI / 4);
      const expectedRfZ = -330.0 * Math.cos(Math.PI / 4);
      assert.ok(Math.abs(rf[0] - expectedRfX) < 1e-4);
      assert.ok(Math.abs(rf[2] - expectedRfZ) < 1e-4);
    });

    it('extends foul lines all the way to the 330 ft fence at the foul pole', () => {
      const halfL = FOUL_LINE_LENGTH / 2;
      const rotY = FOUL_LINE_RIGHT_ROTATION[1];
      // Far endpoint is at local Z = -length / 2
      const farX = FOUL_LINE_RIGHT_POS[0] - halfL * Math.sin(rotY);
      const farZ = FOUL_LINE_RIGHT_POS[2] - halfL * Math.cos(rotY);

      const distFromHome = Math.hypot(farX, farZ);
      assert.ok(
        Math.abs(distFromHome - 330.0) < 0.2,
        `Expected foul line far endpoint to reach 330 ft, got ${distFromHome.toFixed(2)}`,
      );

      // Foul pole position matches far endpoint
      assert.ok(Math.abs(FOUL_POLE_RIGHT_POS[0] - farX) < 0.1);
      assert.ok(Math.abs(FOUL_POLE_RIGHT_POS[2] - farZ) < 0.1);
    });

    it('anchors left foul pole symmetrically at the 330 ft fence intersection', () => {
      const distFromHome = Math.hypot(FOUL_POLE_LEFT_POS[0], FOUL_POLE_LEFT_POS[2]);
      assert.ok(
        Math.abs(distFromHome - 330.0) < 0.2,
        `Expected left foul pole to reach 330 ft, got ${distFromHome.toFixed(2)}`,
      );
      assert.ok(Math.abs(FOUL_POLE_LEFT_POS[0] - (-FOUL_POLE_RIGHT_POS[0])) < 1e-4);
      assert.ok(Math.abs(FOUL_POLE_LEFT_POS[2] - FOUL_POLE_RIGHT_POS[2]) < 1e-4);
    });
  });

  describe('Warning Track Geometry (warningTrackShape)', () => {
    it('is a valid closed THREE.Shape spanning from left to right foul territory', () => {
      assert.ok(warningTrackShape instanceof THREE.Shape);
      const points = warningTrackShape.getPoints();
      assert.ok(points.length >= 32, 'Warning track should have smooth polygonal resolution');
    });

    it('maintains exactly 15 ft width between inner and outer boundary at key field angles', () => {
      // Check CF (0 deg): outer R = 400 ft, inner R = 385 ft
      const shapePoints = warningTrackShape.getPoints();

      assert.ok(pointInPolygon({ x: 0, y: shapeY(-392) }, shapePoints), 'Warning track midpoint at CF should be inside shape');
      assert.equal(pointInPolygon({ x: 0, y: shapeY(-375) }, shapePoints), false, 'Grass inside warning track should NOT be in shape');
    });

    it('does not intersect or overlap the 95-ft infield dirt skirt', () => {
      const shapePoints = warningTrackShape.getPoints();
      // 2B bag is at Z = -127.28, dirt skirt extends to ~Z = -155.5
      assert.equal(pointInPolygon({ x: 0, y: shapeY(-127.28) }, shapePoints), false);
      assert.equal(pointInPolygon({ x: 0, y: shapeY(-155.5) }, shapePoints), false);
    });
  });

  describe('3D Outfield Wall Geometries', () => {
    it('builds wall geometry with height 8 ft and correct radial bounds', () => {
      const wallGeom = createOutfieldWallGeometry();
      wallGeom.computeBoundingBox();
      const bbox = wallGeom.boundingBox!;

      assert.equal(bbox.min.y, 0);
      assert.equal(bbox.max.y, FENCE_WALL_HEIGHT); // 8.0 ft
      // Min Z should be at Center Field (-400 ft) minus thickness
      assert.ok(bbox.min.z <= -400.0);
      // Max X should be at RF boundary (~ +234 ft)
      assert.ok(bbox.max.x >= 230.0);
      assert.ok(bbox.min.x <= -230.0);
    });

    it('builds top cap geometry with height from 8.0 to 8.5 ft', () => {
      const capGeom = createOutfieldWallCapGeometry();
      capGeom.computeBoundingBox();
      const bbox = capGeom.boundingBox!;

      assert.equal(bbox.min.y, FENCE_WALL_HEIGHT); // 8.0 ft
      assert.equal(bbox.max.y, FENCE_WALL_HEIGHT + FENCE_TOP_RAIL_HEIGHT); // 8.5 ft
    });

    it('generates valid vertex normals on the front face pointing toward home plate', () => {
      const wallGeom = createOutfieldWallGeometry();
      const normals = wallGeom.getAttribute('normal');
      const positions = wallGeom.getAttribute('position');
      const indices = wallGeom.getIndex();
      const uvs = wallGeom.getAttribute('uv');

      assert.ok(normals && normals.count > 0, 'Normals attribute must be present');
      assert.ok(positions && positions.count > 0, 'Positions attribute must be present');
      assert.ok(indices && indices.count > 0, 'Geometry must be indexed');
      assert.ok(uvs && uvs.count > 0, 'UV attribute must be present');

      // Center Field front face vertices (at step = 24 of 48, phi = 0)
      // Front vertices are the first (48 + 1) * 2 = 98 vertices:
      // Index for slice 24: 2 * 24 = 48 (bottom) and 49 (top)
      const cfBottomNormal = new THREE.Vector3(normals.getX(48), normals.getY(48), normals.getZ(48));
      const cfTopNormal = new THREE.Vector3(normals.getX(49), normals.getY(49), normals.getZ(49));

      // At CF (phi = 0), normal is [-sin(0), 0, cos(0)] = [0, 0, 1]
      assert.ok(Math.abs(cfBottomNormal.x - 0) < 1e-4);
      assert.equal(cfBottomNormal.y, 0);
      assert.ok(Math.abs(cfBottomNormal.z - 1.0) < 1e-4);
      assert.ok(Math.abs(cfTopNormal.x - 0) < 1e-4);
      assert.equal(cfTopNormal.y, 0);
      assert.ok(Math.abs(cfTopNormal.z - 1.0) < 1e-4);

      // Verify that all front face vertices point toward home plate (+Z)
      const numFrontVertices = (48 + 1) * 2;
      for (let i = 0; i < numFrontVertices; i++) {
        const nz = normals.getZ(i);
        assert.ok(nz > 0, `Front face vertex ${i} normal Z (${nz}) must point toward home plate (+Z)`);
      }
    });

    it('builds indexed top cap geometry with 0.1 ft overhang and valid normals', () => {
      const capGeom = createOutfieldWallCapGeometry();
      const normals = capGeom.getAttribute('normal');
      const positions = capGeom.getAttribute('position');
      const indices = capGeom.getIndex();
      const uvs = capGeom.getAttribute('uv');

      assert.ok(normals && normals.count > 0);
      assert.ok(positions && positions.count > 0);
      assert.ok(indices && indices.count > 0);
      assert.ok(uvs && uvs.count > 0);

      capGeom.computeBoundingBox();
      const bbox = capGeom.boundingBox!;

      // Center field wall radius is 400 ft. With 0.1 ft overhang on front (399.9) and back (401.1):
      // Min Z reaches CF back cap edge at -401.1 ft
      assert.ok(bbox.min.z <= -401.0, `Expected cap min Z <= -401.0, got ${bbox.min.z}`);
      // Max Y is 8.5, Min Y is 8.0
      assert.equal(bbox.min.y, 8.0);
      assert.equal(bbox.max.y, 8.5);

      // Verify top face normal points straight up [0, 1, 0]
      // Top face vertices are offset by (49*2)*2 = 196
      const topVertexOffset = 49 * 2 * 2;
      const topNormalY = normals.getY(topVertexOffset);
      assert.equal(topNormalY, 1.0, 'Top cap top surface normal must point +Y');

      // Verify bottom face normal points straight down [0, -1, 0]
      const bottomVertexOffset = topVertexOffset + 49 * 2;
      const bottomNormalY = normals.getY(bottomVertexOffset);
      assert.equal(bottomNormalY, -1.0, 'Top cap bottom surface normal must point -Y');
    });
  });
});
