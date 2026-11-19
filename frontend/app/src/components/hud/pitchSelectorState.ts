/**
 * pitchSelectorState.ts
 * Pure state manager logic and transitions for PitchSelectorWidget.
 */

export type WidgetViewMode = 'chips' | 'throw';

/**
 * Resolves the initial view mode for the pitch selector widget.
 * By design, the widget displays only the arsenal chips list initially so the player
 * can pick a pitch. The Throw button is hidden until a pitch chip is tapped.
 */
export function resolveInitialWidgetViewMode(
  _selectedPitchName?: string | null,
  _arsenalPitchNames?: string[] | null,
  initialMode?: WidgetViewMode,
): WidgetViewMode {
  return initialMode ?? 'chips';
}

/**
 * Checks whether user is allowed to switch views or select pitches,
 * guarding against pending actions or disabled states.
 */
export function canSwitchOrSelectPitch(
  disabled?: boolean,
  isActionPending?: boolean,
): boolean {
  return !disabled && !isActionPending;
}

/**
 * Determines whether the widget should reset view mode back to 'chips'
 * after a pitch execution finishes (when actionPending transitions from true to false).
 */
export function shouldResetToChipsOnPitchComplete(
  wasActionPending: boolean,
  isActionPending: boolean,
): boolean {
  return wasActionPending && !isActionPending;
}

/**
 * Synchronizes view mode when pitcher repertoire or active pitcher updates.
 * If currently in 'throw' mode and the selected pitch is not in the pitcher's arsenal
 * (e.g. relief pitcher entered who does not throw the pitch), falls back to 'chips' mode.
 */
export function resolveUpdatedWidgetViewMode(
  currentMode: WidgetViewMode,
  selectedPitchName: string | null | undefined,
  arsenalPitchNames?: string[] | null,
): WidgetViewMode {
  const isValid = Boolean(
    selectedPitchName &&
    arsenalPitchNames &&
    arsenalPitchNames.includes(selectedPitchName),
  );
  if (!isValid && currentMode === 'throw') {
    return 'chips';
  }
  return currentMode;
}
