import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { useGameStore } from '../gameStore';

describe('gameStore Batted Ball Pause State', () => {
  it('initializes isBattedBallPaused as false', () => {
    assert.equal(useGameStore.getState().isBattedBallPaused, false);
  });

  it('sets isBattedBallPaused explicitly and via toggle', () => {
    useGameStore.getState().setBattedBallPaused(true);
    assert.equal(useGameStore.getState().isBattedBallPaused, true);

    useGameStore.getState().toggleBattedBallPaused();
    assert.equal(useGameStore.getState().isBattedBallPaused, false);

    useGameStore.getState().toggleBattedBallPaused();
    assert.equal(useGameStore.getState().isBattedBallPaused, true);

    useGameStore.getState().setBattedBallPaused(false);
    assert.equal(useGameStore.getState().isBattedBallPaused, false);
  });
});
