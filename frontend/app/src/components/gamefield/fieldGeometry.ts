import * as THREE from 'three';

/**
 * A ShapeGeometry built in XY and rotated [-Math.PI / 2, 0, 0] maps
 * local (x, y) to world (x, 0, -y). Field-space Z therefore becomes
 * shape-space Y = -z, keeping every shape in FRONT of the camera (-Z).
 */
export const shapeY = (z: number): number => -z;

/** Infield dirt skirt: home plate, both foul edges, and the 95-ft arc. */
export const dirtSkirtShape: THREE.Shape = new THREE.Shape();
dirtSkirtShape.moveTo(0, shapeY(0));
dirtSkirtShape.lineTo(-63.64, shapeY(-63.64)); // 3B edge
// Mirror of the brief's 1.25π → 1.75π arc once Y is negated.
dirtSkirtShape.absarc(0, shapeY(-60.5), 95, Math.PI * 0.75, Math.PI * 0.25, true);
dirtSkirtShape.lineTo(63.64, shapeY(-63.64)); // 1B edge
dirtSkirtShape.closePath();

/** 90x90 ft infield grass diamond with a 9-ft pitcher's-mound cutout. */
export const infieldGrassShape: THREE.Shape = new THREE.Shape();
infieldGrassShape.moveTo(0, shapeY(-1.5));
infieldGrassShape.lineTo(-61.5, shapeY(-63.64));
infieldGrassShape.lineTo(0, shapeY(-125.0));
infieldGrassShape.lineTo(61.5, shapeY(-63.64));
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
export const FOUL_LINE_LEFT_POS: [number, number, number] = [-113, 0.012, -113];
export const FOUL_LINE_RIGHT_POS: [number, number, number] = [113, 0.012, -113];
export const FOUL_LINE_LEFT_ROTATION: [number, number, number] = [0, Math.PI / 4, 0];
export const FOUL_LINE_RIGHT_ROTATION: [number, number, number] = [0, -Math.PI / 4, 0];
export const FOUL_LINE_LENGTH: number = 319.611;

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
export const BATTERS_BOX_LEFT_POS: [number, number, number] = [-3.21, 0.012, -0.71];
export const BATTERS_BOX_RIGHT_POS: [number, number, number] = [3.21, 0.012, -0.71];
