/**
 * Plate-discipline swing/take model.
 *
 * Mirrors backend/engine/batting_engine/batter_strategy.py. Keep the shared
 * swingModelConfig.json files in sync; tests enforce that.
 */

import swingModelConfig from './swingModelConfig.json';
import {
  evaluateSwingWithConfig,
  type SwingDelivery,
  type SwingEvaluation,
  type SwingRatings,
  type SwingSituation,
} from './swingDecisionCore';

export * from './swingDecisionCore';

const CONFIG: any = swingModelConfig;

export function evaluateSwing(
  delivery: SwingDelivery,
  ratings: SwingRatings,
  situation: SwingSituation,
  rng?: () => number,
): SwingEvaluation {
  return evaluateSwingWithConfig(CONFIG, delivery, ratings, situation, rng);
}
