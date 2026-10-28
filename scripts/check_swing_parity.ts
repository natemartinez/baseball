/**
 * Backend/frontend parity check for the plate-discipline model.
 *
 * Run with Node 24:
 *   node --experimental-strip-types scripts/check_swing_parity.ts
 */

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { evaluateSwingWithConfig } from '../frontend/app/src/services/swingDecisionCore.ts';

const here = dirname(fileURLToPath(import.meta.url));
const config = JSON.parse(
  readFileSync(
    resolve(here, '../backend/engine/batting_engine/swing_model_config.json'),
    'utf8',
  ),
);
const cases = JSON.parse(
  readFileSync(resolve(here, '../tests/fixtures/swing_model_parity_cases.json'), 'utf8'),
);

let failures = 0;
for (const [index, entry] of cases.entries()) {
  const evaluation = evaluateSwingWithConfig(
    config,
    entry.delivery,
    entry.ratings,
    entry.situation,
  );
  const diff = Math.abs(evaluation.probability - entry.expectedProbability);
  if (diff > 1e-6) {
    failures += 1;
    console.error(
      `case ${index}: expected ${entry.expectedProbability}, got ${evaluation.probability} (diff ${diff})`,
    );
  }
}

if (failures > 0) {
  console.error(`${failures}/${cases.length} parity cases failed`);
  process.exit(1);
}

console.log(`${cases.length}/${cases.length} swing-model parity cases passed`);
