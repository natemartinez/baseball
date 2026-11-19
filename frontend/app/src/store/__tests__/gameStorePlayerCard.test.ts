import { describe, it } from 'node:test';
import assert from 'node:assert';
import { useGameStore } from '../gameStore.ts';

describe('gameStore Player Card Modal state', () => {
  it('initializes isPlayerCardModalOpen as false', () => {
    const state = useGameStore.getState();
    assert.strictEqual(state.isPlayerCardModalOpen, false);
  });

  it('toggles isPlayerCardModalOpen with explicit boolean or toggle', () => {
    const { togglePlayerCardModal } = useGameStore.getState();
    assert.strictEqual(typeof togglePlayerCardModal, 'function');

    togglePlayerCardModal(true);
    assert.strictEqual(useGameStore.getState().isPlayerCardModalOpen, true);

    togglePlayerCardModal(false);
    assert.strictEqual(useGameStore.getState().isPlayerCardModalOpen, false);

    togglePlayerCardModal();
    assert.strictEqual(useGameStore.getState().isPlayerCardModalOpen, true);

    togglePlayerCardModal();
    assert.strictEqual(useGameStore.getState().isPlayerCardModalOpen, false);
  });

  it('dismisses other active menus when opening player card modal to prevent iOS modal conflict', () => {
    const { toggleSettingsMenu, toggleStrategyMenu, togglePlayerCardModal } = useGameStore.getState();
    toggleSettingsMenu(true);
    toggleStrategyMenu(true);
    assert.strictEqual(useGameStore.getState().isSettingsMenuOpen, true);
    assert.strictEqual(useGameStore.getState().isStrategyMenuOpen, true);

    togglePlayerCardModal(true);
    assert.strictEqual(useGameStore.getState().isPlayerCardModalOpen, true);
    assert.strictEqual(useGameStore.getState().isSettingsMenuOpen, false);
    assert.strictEqual(useGameStore.getState().isStrategyMenuOpen, false);

    togglePlayerCardModal(false);
    assert.strictEqual(useGameStore.getState().isPlayerCardModalOpen, false);
  });
});

