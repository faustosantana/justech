/**
 * Orden de visualización de señales (no es “fuerza matemática oficial”).
 * Determinista y documentado para UI.
 */
export type SignalSortInput = {
  number: number;
  confirmation_count: number;
  evaluable_cases: number;
  rate_within_3: number | null;
  typical_cycle: number | null;
};

export function compareSignalsForDisplay(a: SignalSortInput, b: SignalSortInput): number {
  if (b.confirmation_count !== a.confirmation_count) {
    return b.confirmation_count - a.confirmation_count;
  }
  if (b.evaluable_cases !== a.evaluable_cases) {
    return b.evaluable_cases - a.evaluable_cases;
  }
  const ra = a.rate_within_3 ?? -1;
  const rb = b.rate_within_3 ?? -1;
  if (rb !== ra) return rb - ra;
  const ca = a.typical_cycle ?? Number.POSITIVE_INFINITY;
  const cb = b.typical_cycle ?? Number.POSITIVE_INFINITY;
  if (ca !== cb) return ca - cb;
  return a.number - b.number;
}

export function sortSignalsForDisplay<T extends SignalSortInput>(items: T[]): T[] {
  return [...items].sort(compareSignalsForDisplay);
}
