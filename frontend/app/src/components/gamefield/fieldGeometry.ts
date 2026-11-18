import * as THREE from 'three';

/**
 * A ShapeGeometry built in XY and rotated [-Math.PI / 2, 0, 0] maps
 * local (x, y) to world (x, 0, -y). Field-space Z therefore becomes
 * shape-space Y = -z, keeping every shape in FRONT of the camera (-Z).
 */
export const shapeY = (z: number): number => -z;

/**
 * Regulation 95-ft infield dirt arc radius and boundary intersections.
 * Center is front of pitcher's rubber at (0, -60.5).
 * Intersects outer baseline foul boundary (offset 3 ft into foul territory, X + Z = 4.2426)
 * at X = ±91.2322 ft, Z = -86.9895 ft.
 */
export const INFIELD_DIRT_ARC_RADIUS: number = 95.0;
export const DIRT_SKIRT_INTERSECT_1B: [number, number] = [91.2322, -86.9895];
export const DIRT_SKIRT_INTERSECT_3B: [number, number] = [-91.2322, -86.9895];

const dirtArcAngle1B = Math.atan2(shapeY(DIRT_SKIRT_INTERSECT_1B[1]) - 60.5, DIRT_SKIRT_INTERSECT_1B[0]); // ~0.282583 rad (16.19 deg)
const dirtArcAngle3B = Math.PI - dirtArcAngle1B; // ~2.859010 rad (163.81 deg)

/** Infield dirt skirt: home plate, both foul boundaries, and the full 95-ft arc. */
export const dirtSkirtShape: THREE.Shape = new THREE.Shape();
dirtSkirtShape.moveTo(0, shapeY(0));
dirtSkirtShape.lineTo(DIRT_SKIRT_INTERSECT_3B[0], shapeY(DIRT_SKIRT_INTERSECT_3B[1]));
dirtSkirtShape.absarc(0, shapeY(-60.5), INFIELD_DIRT_ARC_RADIUS, dirtArcAngle3B, dirtArcAngle1B, true);
dirtSkirtShape.lineTo(0, shapeY(0));
dirtSkirtShape.closePath();

/**
 * 26-ft diameter (13-ft radius) home plate sand/dirt circle.
 * Encompasses home plate, both batter's boxes, and the catcher/umpire area.
 */
export const HOME_PLATE_CIRCLE_RADIUS: number = 13.0;
export const HOME_PLATE_CIRCLE_POS: [number, number, number] = [0, 0.020, 0];

export const homePlateCircleShape: THREE.Shape = new THREE.Shape();
homePlateCircleShape.absarc(0, 0, HOME_PLATE_CIRCLE_RADIUS, 0, Math.PI * 2, false);

/** 
 * 90x90 ft infield grass diamond with base sliding pit cutouts (1B, 2B, 3B),
 * 3.5-ft running lane dirt setbacks along the baselines, a 9-ft pitcher's-mound
 * cutout, and a 13-ft home plate circle cutout.
 */
export const BASE_SLIDING_PIT_RADIUS: number = 10.0;
export const BASELINE_RUNNING_LANE_SETBACK: number = 3.5;

// Quadratic intersection of X^2 + (X + dFairSqrt2)^2 = HOME_PLATE_CIRCLE_RADIUS^2
const dFairSqrt2 = BASELINE_RUNNING_LANE_SETBACK * Math.sqrt(2);
const aHome = 2.0;
const bHome = 2.0 * dFairSqrt2;
const cHome = dFairSqrt2 * dFairSqrt2 - HOME_PLATE_CIRCLE_RADIUS * HOME_PLATE_CIRCLE_RADIUS;
const xHome = (-bHome + Math.sqrt(bHome * bHome - 4 * aHome * cHome)) / (2 * aHome); // ~6.3781 ft
const yHome = xHome + dFairSqrt2; // ~11.3278 ft
const angleHome1B = Math.atan2(yHome, xHome); // ~1.057992 rad (60.62 deg)
const angleHome3B = Math.PI - angleHome1B; // ~2.083601 rad (119.38 deg)

// Intersection of fair setback line with 1B sliding pit circle (center: 63.64, 63.64; radius: 10.0)
const aPit = 2.0;
const bPit = 2.0 * dFairSqrt2;
const cPit = dFairSqrt2 * dFairSqrt2 - BASE_SLIDING_PIT_RADIUS * BASE_SLIDING_PIT_RADIUS;
const uPit = (-bPit - Math.sqrt(bPit * bPit - 4 * aPit * cPit)) / (2 * aPit);
const x1bPit = 63.64 + uPit; // ~54.5413 ft
const y1bPit = x1bPit + dFairSqrt2; // ~59.4911 ft
const angle1bPit = Math.atan2(y1bPit - 63.64, x1bPit - 63.64); // ~ -2.713766 rad (-155.49 deg)
const angle3bPit = Math.atan2(y1bPit - 63.64, -(x1bPit - 63.64)); // ~ -0.427827 rad (-24.51 deg)

const rPitCos = BASE_SLIDING_PIT_RADIUS * Math.cos(Math.PI / 4);
const rPitSin = BASE_SLIDING_PIT_RADIUS * Math.sin(Math.PI / 4);

export const infieldGrassShape: THREE.Shape = new THREE.Shape();
// Start at home plate circle intersection on 1B side
infieldGrassShape.moveTo(xHome, yHome);

// Running lane setback to 1B sliding pit cutout
infieldGrassShape.lineTo(x1bPit, y1bPit);
infieldGrassShape.absarc(
  63.64,
  shapeY(-63.64),
  BASE_SLIDING_PIT_RADIUS,
  angle1bPit,
  Math.PI * 0.75,
  true,
);

// Baseline towards 2B and 2B sliding pit cutout (centered at 2B: 0, shapeY(-127.28))
infieldGrassShape.lineTo(0 + rPitCos, shapeY(-127.28) - rPitSin);
infieldGrassShape.absarc(
  0,
  shapeY(-127.28),
  BASE_SLIDING_PIT_RADIUS,
  -Math.PI * 0.25,
  -Math.PI * 0.75,
  true,
);

// Baseline towards 3B and 3B sliding pit cutout (centered at 3B: -63.64, shapeY(-63.64))
infieldGrassShape.lineTo(-63.64 + rPitCos, shapeY(-63.64) + rPitSin);
infieldGrassShape.absarc(
  -63.64,
  shapeY(-63.64),
  BASE_SLIDING_PIT_RADIUS,
  Math.PI * 0.25,
  angle3bPit,
  true,
);

// Running lane setback back to home plate circle cutout
infieldGrassShape.lineTo(-xHome, yHome);
infieldGrassShape.absarc(
  0,
  0,
  HOME_PLATE_CIRCLE_RADIUS,
  angleHome3B,
  angleHome1B,
  true,
);
infieldGrassShape.closePath();

const moundHole: THREE.Path = new THREE.Path();
moundHole.absarc(0, shapeY(-59.0), 9, 0, Math.PI * 2, false);
infieldGrassShape.holes.push(moundHole);

/** 17 in x 17 in home plate: rear apex at origin, forward = +shape Y. */
const halfWidth: number = 17 / 12 / 2; // 0.70833 ft
const depth: number = 17 / 12; // 1.41667 ft

export const homePlateShape: THREE.Shape = new THREE.Shape();
homePlateShape.moveTo(0, 0);
homePlateShape.lineTo(-halfWidth, shapeY(-halfWidth));
homePlateShape.lineTo(-halfWidth, shapeY(-depth));
homePlateShape.lineTo(halfWidth, shapeY(-depth));
homePlateShape.lineTo(halfWidth, shapeY(-halfWidth));
homePlateShape.closePath();

/** Home plate dimensions (feet), shared with the screen-space plate projection. */
export const HOME_PLATE_HALF_WIDTH: number = halfWidth;
export const HOME_PLATE_DEPTH: number = depth;

/** Scene placement constants (feet). */
export const MOUND_POS: [number, number, number] = [0, 0.415, -59.0];
export const RUBBER_POS: [number, number, number] = [0, 0.84, -60.5];
export const BASE_1B_POS: [number, number, number] = [63.64, 0.1, -63.64];
export const BASE_2B_POS: [number, number, number] = [0, 0.1, -127.28];
export const BASE_3B_POS: [number, number, number] = [-63.64, 0.1, -63.64];

/** 4x6 ft Batter's Box Outline (Chalk Line) */
export const battersBoxShape = new THREE.Shape();
const boxWidth = 4.0;
const boxLength = 6.0;
const lineThickness = 0.15; // ~2 inch chalk line

// Outer boundary
battersBoxShape.moveTo(-boxWidth / 2, -boxLength / 2);
battersBoxShape.lineTo(-boxWidth / 2, boxLength / 2);
battersBoxShape.lineTo(boxWidth / 2, boxLength / 2);
battersBoxShape.lineTo(boxWidth / 2, -boxLength / 2);
battersBoxShape.closePath();

// Inner cutout (hole) to make it an outline
const boxHole = new THREE.Path();
const iw = boxWidth / 2 - lineThickness;
const il = boxLength / 2 - lineThickness;
boxHole.moveTo(-iw, -il);
boxHole.lineTo(-iw, il);
boxHole.lineTo(iw, il);
boxHole.lineTo(iw, -il);
boxHole.closePath();
battersBoxShape.holes.push(boxHole);

/** 
 * Batter's Box Placement
 * Home plate is 17" wide (0.708ft from center). Gap is 6" (0.5ft). 
 * Box center X is 0.708 + 0.5 + 2.0 = 3.208 ft.
 * Box center Z aligns with center of home plate (8.5" or 0.708ft forward of the apex).
 */
export const BATTERS_BOX_LEFT_POS: [number, number, number] = [-3.21, 0.060, -0.71];
export const BATTERS_BOX_RIGHT_POS: [number, number, number] = [3.21, 0.060, -0.71];

/**
 * Outfield Fence & Regulation Ballpark Dimensions
 * Matching backend batting engine (contact_outcome.py) and MLB standards.
 */
export const FENCE_CENTER_DISTANCE = 400.0;
export const FENCE_FOUL_LINE_DISTANCE = 330.0;
export const FENCE_WALL_HEIGHT = 8.0;
export const FENCE_WALL_THICKNESS = 1.0;
export const FENCE_TOP_RAIL_HEIGHT = 0.5;
export const WARNING_TRACK_WIDTH = 15.0;
export const FOUL_POLE_HEIGHT = 32.0;
export const FOUL_POLE_RADIUS = 0.4;

/**
 * Calculates distance to the outfield wall at a given spray angle (degrees).
 * Angle convention: 0 = Center Field, +45 = Right Field Line, -45 = Left Field Line.
 * Symmetrically interpolates between 400 ft (center) and 330 ft (corners).
 */
export function fenceDistance(sprayAngleDeg: number): number {
  const fraction = Math.min(Math.abs(sprayAngleDeg), 45.0) / 45.0;
  return FENCE_CENTER_DISTANCE - (FENCE_CENTER_DISTANCE - FENCE_FOUL_LINE_DISTANCE) * fraction;
}

/**
 * Returns the [x, y, z] 3D world coordinate on the outfield fence curve for a given spray angle.
 * Three.js coordinate system: +X = Right, +Y = Up, -Z = Forward (Center Field).
 */
export function getFencePoint(sprayAngleDeg: number, radialOffset: number = 0): [number, number, number] {
  const rad = (sprayAngleDeg * Math.PI) / 180.0;
  const r = fenceDistance(sprayAngleDeg) + radialOffset;
  return [r * Math.sin(rad), 0, -r * Math.cos(rad)];
}

/**
 * Procedural Warning Track Shape
 * Follows the outfield fence from left foul boundary (-48 deg) to right foul boundary (+48 deg),
 * maintaining a 15-ft width (R_inner = fenceDistance(phi) - WARNING_TRACK_WIDTH) before closing.
 */
export const WARNING_TRACK_ANGLE_MIN = -48.0;
export const WARNING_TRACK_ANGLE_MAX = 48.0;
export const WARNING_TRACK_STEPS = 48;

export const warningTrackShape: THREE.Shape = new THREE.Shape();

// 1. Outer boundary points from -48 deg to +48 deg
for (let i = 0; i <= WARNING_TRACK_STEPS; i++) {
  const angleDeg =
    WARNING_TRACK_ANGLE_MIN + (i / WARNING_TRACK_STEPS) * (WARNING_TRACK_ANGLE_MAX - WARNING_TRACK_ANGLE_MIN);
  const rad = (angleDeg * Math.PI) / 180.0;
  const rOuter = fenceDistance(angleDeg);
  const x = rOuter * Math.sin(rad);
  const y = rOuter * Math.cos(rad);
  if (i === 0) {
    warningTrackShape.moveTo(x, y);
  } else {
    warningTrackShape.lineTo(x, y);
  }
}

// 2. Inner boundary points reverse sweep from +48 deg back to -48 deg
for (let i = WARNING_TRACK_STEPS; i >= 0; i--) {
  const angleDeg =
    WARNING_TRACK_ANGLE_MIN + (i / WARNING_TRACK_STEPS) * (WARNING_TRACK_ANGLE_MAX - WARNING_TRACK_ANGLE_MIN);
  const rad = (angleDeg * Math.PI) / 180.0;
  const rInner = fenceDistance(angleDeg) - WARNING_TRACK_WIDTH;
  const x = rInner * Math.sin(rad);
  const y = rInner * Math.cos(rad);
  warningTrackShape.lineTo(x, y);
}

// 3. Close the warning track polygon
warningTrackShape.closePath();

/**
 * Baserunning / Foul Line Placement
 * Both lines meet at the top-middle of the respective batter's boxes
 * (X = ±3.21, Z = -3.71) rather than converging at the rear apex of home plate (0, 0, 0),
 * pass straight through 1B (63.64, -63.64) and 3B (-63.64, -63.64) into the outfield,
 * and extend to intersect the outfield fence circle at R = 330.0 ft (X = ±234.05, Z = -232.64).
 */
const rightBoxTopMiddleX = BATTERS_BOX_RIGHT_POS[0];
const rightBoxTopMiddleZ = BATTERS_BOX_RIGHT_POS[2] - boxLength / 2; // -3.71

const foulLineDx = BASE_1B_POS[0] - rightBoxTopMiddleX; // 60.43
const foulLineDz = BASE_1B_POS[2] - rightBoxTopMiddleZ; // -59.93
const foulLineAngle = Math.atan2(foulLineDx, -foulLineDz);

// Solve quadratic intersection of foul line ray (x0 + t*dx, z0 + t*dz) with circle of radius R = 330.0 ft
const aFoul = foulLineDx * foulLineDx + foulLineDz * foulLineDz;
const bFoul = 2 * (rightBoxTopMiddleX * foulLineDx + rightBoxTopMiddleZ * foulLineDz);
const cFoul =
  rightBoxTopMiddleX * rightBoxTopMiddleX +
  rightBoxTopMiddleZ * rightBoxTopMiddleZ -
  FENCE_FOUL_LINE_DISTANCE * FENCE_FOUL_LINE_DISTANCE;
const tOutfield = (-bFoul + Math.sqrt(bFoul * bFoul - 4 * aFoul * cFoul)) / (2 * aFoul);

const outfieldEndX = rightBoxTopMiddleX + tOutfield * foulLineDx;
const outfieldZ = rightBoxTopMiddleZ + tOutfield * foulLineDz;

export const FOUL_POLE_LEFT_POS: [number, number, number] = [-outfieldEndX, 0.0, outfieldZ];
export const FOUL_POLE_RIGHT_POS: [number, number, number] = [outfieldEndX, 0.0, outfieldZ];

export const FOUL_LINE_LENGTH: number = Math.hypot(
  outfieldEndX - rightBoxTopMiddleX,
  outfieldZ - rightBoxTopMiddleZ,
);

const foulLineCenterX = (rightBoxTopMiddleX + outfieldEndX) / 2;
const foulLineCenterZ = (rightBoxTopMiddleZ + outfieldZ) / 2;

export const FOUL_LINE_LEFT_POS: [number, number, number] = [-foulLineCenterX, 0.060, foulLineCenterZ];
export const FOUL_LINE_RIGHT_POS: [number, number, number] = [foulLineCenterX, 0.060, foulLineCenterZ];
export const FOUL_LINE_LEFT_ROTATION: [number, number, number] = [0, foulLineAngle, 0];
export const FOUL_LINE_RIGHT_ROTATION: [number, number, number] = [0, -foulLineAngle, 0];

/**
 * Outfield fence sweep angle parameters.
 * Covers left foul boundary (-48 deg) to right foul boundary (+48 deg).
 */
export const FENCE_ANGLE_MIN = -48.0;
export const FENCE_ANGLE_MAX = 48.0;
export const FENCE_STEPS = 48;
export const FENCE_CAP_EXTRA_WIDTH = 0.1;

/**
 * Creates the procedural 3D BufferGeometry for the 8-ft outfield wall.
 * Constructs front face (R_f), back face (R_b), and left/right end caps with smooth normals.
 */
export function createOutfieldWallGeometry(steps: number = FENCE_STEPS): THREE.BufferGeometry {
  const positions: number[] = [];
  const normals: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];

  const yMin = 0;
  const yMax = FENCE_WALL_HEIGHT;

  // Precompute angles, radii, and coordinates for all slices
  const slices: {
    rad: number;
    sin: number;
    cos: number;
    rf: number;
    rb: number;
    xf: number;
    zf: number;
    xb: number;
    zb: number;
  }[] = [];

  for (let i = 0; i <= steps; i++) {
    const angleDeg = FENCE_ANGLE_MIN + (i / steps) * (FENCE_ANGLE_MAX - FENCE_ANGLE_MIN);
    const rad = (angleDeg * Math.PI) / 180.0;
    const sin = Math.sin(rad);
    const cos = Math.cos(rad);
    const rf = fenceDistance(angleDeg);
    const rb = rf + FENCE_WALL_THICKNESS;
    slices.push({
      rad,
      sin,
      cos,
      rf,
      rb,
      xf: rf * sin,
      zf: -rf * cos,
      xb: rb * sin,
      zb: -rb * cos,
    });
  }

  // 1. Front Surface (faces home plate, normals point inward: [-sin, 0, cos])
  const frontVertexOffset = positions.length / 3;
  for (let i = 0; i <= steps; i++) {
    const s = slices[i];
    const u = i / steps;
    // Bottom vertex
    positions.push(s.xf, yMin, s.zf);
    normals.push(-s.sin, 0, s.cos);
    uvs.push(u, 0);

    // Top vertex
    positions.push(s.xf, yMax, s.zf);
    normals.push(-s.sin, 0, s.cos);
    uvs.push(u, 1);
  }

  for (let i = 0; i < steps; i++) {
    const b0 = frontVertexOffset + 2 * i;
    const t0 = b0 + 1;
    const b1 = frontVertexOffset + 2 * (i + 1);
    const t1 = b1 + 1;
    // Triangle 1: b0, b1, t1
    // Triangle 2: b0, t1, t0
    indices.push(b0, b1, t1);
    indices.push(b0, t1, t0);
  }

  // 2. Back Surface (faces outside stadium, normals point outward: [sin, 0, -cos])
  const backVertexOffset = positions.length / 3;
  for (let i = 0; i <= steps; i++) {
    const s = slices[i];
    const u = i / steps;
    // Bottom vertex
    positions.push(s.xb, yMin, s.zb);
    normals.push(s.sin, 0, -s.cos);
    uvs.push(u, 0);

    // Top vertex
    positions.push(s.xb, yMax, s.zb);
    normals.push(s.sin, 0, -s.cos);
    uvs.push(u, 1);
  }

  for (let i = 0; i < steps; i++) {
    const b0 = backVertexOffset + 2 * i;
    const t0 = b0 + 1;
    const b1 = backVertexOffset + 2 * (i + 1);
    const t1 = b1 + 1;
    indices.push(b1, b0, t0);
    indices.push(b1, t0, t1);
  }

  // 3. Left End Cap (at phi = -48 deg, i = 0)
  // Outward normal: -tangent = [-cos(phi0), 0, -sin(phi0)]
  const s0 = slices[0];
  const leftNormal: [number, number, number] = [-s0.cos, 0, -s0.sin];
  const leftVertexOffset = positions.length / 3;

  positions.push(
    s0.xb, yMin, s0.zb, // 0: back bottom
    s0.xf, yMin, s0.zf, // 1: front bottom
    s0.xf, yMax, s0.zf, // 2: front top
    s0.xb, yMax, s0.zb, // 3: back top
  );
  for (let k = 0; k < 4; k++) {
    normals.push(...leftNormal);
  }
  uvs.push(0, 0, 1, 0, 1, 1, 0, 1);
  indices.push(
    leftVertexOffset + 0,
    leftVertexOffset + 1,
    leftVertexOffset + 2,
    leftVertexOffset + 0,
    leftVertexOffset + 2,
    leftVertexOffset + 3,
  );

  // 4. Right End Cap (at phi = +48 deg, i = steps)
  // Outward normal: +tangent = [cos(phiN), 0, sin(phiN)]
  const sN = slices[steps];
  const rightNormal: [number, number, number] = [sN.cos, 0, sN.sin];
  const rightVertexOffset = positions.length / 3;

  positions.push(
    sN.xf, yMin, sN.zf, // 0: front bottom
    sN.xb, yMin, sN.zb, // 1: back bottom
    sN.xb, yMax, sN.zb, // 2: back top
    sN.xf, yMax, sN.zf, // 3: front top
  );
  for (let k = 0; k < 4; k++) {
    normals.push(...rightNormal);
  }
  uvs.push(0, 0, 1, 0, 1, 1, 0, 1);
  indices.push(
    rightVertexOffset + 0,
    rightVertexOffset + 1,
    rightVertexOffset + 2,
    rightVertexOffset + 0,
    rightVertexOffset + 2,
    rightVertexOffset + 3,
  );

  const geom = new THREE.BufferGeometry();
  geom.setIndex(indices);
  geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geom.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
  geom.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geom.computeBoundingBox();
  geom.computeBoundingSphere();
  return geom;
}

/**
 * Creates the procedural 3D BufferGeometry for the top rail cap.
 * Spans from Y = 8.0 to Y = 8.5 ft, and radially from R_f - 0.1 to R_b + 0.1 ft.
 */
export function createOutfieldWallCapGeometry(steps: number = FENCE_STEPS): THREE.BufferGeometry {
  const positions: number[] = [];
  const normals: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];

  const yMin = FENCE_WALL_HEIGHT;
  const yMax = FENCE_WALL_HEIGHT + FENCE_TOP_RAIL_HEIGHT;

  const slices: {
    rad: number;
    sin: number;
    cos: number;
    rcf: number;
    rcb: number;
    xcf: number;
    zcf: number;
    xcb: number;
    zcb: number;
  }[] = [];

  for (let i = 0; i <= steps; i++) {
    const angleDeg = FENCE_ANGLE_MIN + (i / steps) * (FENCE_ANGLE_MAX - FENCE_ANGLE_MIN);
    const rad = (angleDeg * Math.PI) / 180.0;
    const sin = Math.sin(rad);
    const cos = Math.cos(rad);
    const rf = fenceDistance(angleDeg);
    const rcf = rf - FENCE_CAP_EXTRA_WIDTH;
    const rcb = rf + FENCE_WALL_THICKNESS + FENCE_CAP_EXTRA_WIDTH;
    slices.push({
      rad,
      sin,
      cos,
      rcf,
      rcb,
      xcf: rcf * sin,
      zcf: -rcf * cos,
      xcb: rcb * sin,
      zcb: -rcb * cos,
    });
  }

  // 1. Cap Front Surface (faces home plate, normals: [-sin, 0, cos])
  const frontVertexOffset = positions.length / 3;
  for (let i = 0; i <= steps; i++) {
    const s = slices[i];
    const u = i / steps;
    positions.push(s.xcf, yMin, s.zcf);
    normals.push(-s.sin, 0, s.cos);
    uvs.push(u, 0);

    positions.push(s.xcf, yMax, s.zcf);
    normals.push(-s.sin, 0, s.cos);
    uvs.push(u, 1);
  }

  for (let i = 0; i < steps; i++) {
    const b0 = frontVertexOffset + 2 * i;
    const t0 = b0 + 1;
    const b1 = frontVertexOffset + 2 * (i + 1);
    const t1 = b1 + 1;
    indices.push(b0, b1, t1);
    indices.push(b0, t1, t0);
  }

  // 2. Cap Back Surface (faces outside stadium, normals: [sin, 0, -cos])
  const backVertexOffset = positions.length / 3;
  for (let i = 0; i <= steps; i++) {
    const s = slices[i];
    const u = i / steps;
    positions.push(s.xcb, yMin, s.zcb);
    normals.push(s.sin, 0, -s.cos);
    uvs.push(u, 0);

    positions.push(s.xcb, yMax, s.zcb);
    normals.push(s.sin, 0, -s.cos);
    uvs.push(u, 1);
  }

  for (let i = 0; i < steps; i++) {
    const b0 = backVertexOffset + 2 * i;
    const t0 = b0 + 1;
    const b1 = backVertexOffset + 2 * (i + 1);
    const t1 = b1 + 1;
    indices.push(b1, b0, t0);
    indices.push(b1, t0, t1);
  }

  // 3. Cap Top Surface (Y = yMax = 8.5, normal: [0, 1, 0])
  const topVertexOffset = positions.length / 3;
  for (let i = 0; i <= steps; i++) {
    const s = slices[i];
    const u = i / steps;
    positions.push(s.xcf, yMax, s.zcf);
    normals.push(0, 1, 0);
    uvs.push(u, 0);

    positions.push(s.xcb, yMax, s.zcb);
    normals.push(0, 1, 0);
    uvs.push(u, 1);
  }

  for (let i = 0; i < steps; i++) {
    const f0 = topVertexOffset + 2 * i;
    const b0 = f0 + 1;
    const f1 = topVertexOffset + 2 * (i + 1);
    const b1 = f1 + 1;
    indices.push(f0, f1, b1);
    indices.push(f0, b1, b0);
  }

  // 4. Cap Bottom Surface (Y = yMin = 8.0, normal: [0, -1, 0])
  const bottomVertexOffset = positions.length / 3;
  for (let i = 0; i <= steps; i++) {
    const s = slices[i];
    const u = i / steps;
    positions.push(s.xcf, yMin, s.zcf);
    normals.push(0, -1, 0);
    uvs.push(u, 0);

    positions.push(s.xcb, yMin, s.zcb);
    normals.push(0, -1, 0);
    uvs.push(u, 1);
  }

  for (let i = 0; i < steps; i++) {
    const f0 = bottomVertexOffset + 2 * i;
    const b0 = f0 + 1;
    const f1 = bottomVertexOffset + 2 * (i + 1);
    const b1 = f1 + 1;
    indices.push(f0, b1, f1);
    indices.push(f0, b0, b1);
  }

  // 5. Cap Left End Cap (phi = -48 deg, i = 0)
  const s0 = slices[0];
  const leftNormal: [number, number, number] = [-s0.cos, 0, -s0.sin];
  const leftVertexOffset = positions.length / 3;

  positions.push(
    s0.xcb, yMin, s0.zcb, // 0: back bottom
    s0.xcf, yMin, s0.zcf, // 1: front bottom
    s0.xcf, yMax, s0.zcf, // 2: front top
    s0.xcb, yMax, s0.zcb, // 3: back top
  );
  for (let k = 0; k < 4; k++) {
    normals.push(...leftNormal);
  }
  uvs.push(0, 0, 1, 0, 1, 1, 0, 1);
  indices.push(
    leftVertexOffset + 0,
    leftVertexOffset + 1,
    leftVertexOffset + 2,
    leftVertexOffset + 0,
    leftVertexOffset + 2,
    leftVertexOffset + 3,
  );

  // 6. Cap Right End Cap (phi = +48 deg, i = steps)
  const sN = slices[steps];
  const rightNormal: [number, number, number] = [sN.cos, 0, sN.sin];
  const rightVertexOffset = positions.length / 3;

  positions.push(
    sN.xcf, yMin, sN.zcf, // 0: front bottom
    sN.xcb, yMin, sN.zcb, // 1: back bottom
    sN.xcb, yMax, sN.zcb, // 2: back top
    sN.xcf, yMax, sN.zcf, // 3: front top
  );
  for (let k = 0; k < 4; k++) {
    normals.push(...rightNormal);
  }
  uvs.push(0, 0, 1, 0, 1, 1, 0, 1);
  indices.push(
    rightVertexOffset + 0,
    rightVertexOffset + 1,
    rightVertexOffset + 2,
    rightVertexOffset + 0,
    rightVertexOffset + 2,
    rightVertexOffset + 3,
  );

  const geom = new THREE.BufferGeometry();
  geom.setIndex(indices);
  geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geom.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
  geom.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geom.computeBoundingBox();
  geom.computeBoundingSphere();
  return geom;
}
