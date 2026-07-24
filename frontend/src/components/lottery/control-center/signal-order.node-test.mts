/**
 * Unit checks for signal-order.ts (Node, no vitest in this package).
 * Run: node --experimental-strip-types frontend/src/components/lottery/control-center/signal-order.node-test.mts
 */
import { compareSignalsForDisplay, sortSignalsForDisplay } from "./signal-order.ts";

function assert(cond: unknown, msg: string) {
  if (!cond) throw new Error(msg);
}

const items = [
  { number: 9, confirmation_count: 1, evaluable_cases: 10, rate_within_3: 0.5, typical_cycle: 3 },
  { number: 4, confirmation_count: 2, evaluable_cases: 5, rate_within_3: 0.2, typical_cycle: 4 },
  { number: 2, confirmation_count: 2, evaluable_cases: 8, rate_within_3: 0.2, typical_cycle: 2 },
  { number: 7, confirmation_count: 2, evaluable_cases: 8, rate_within_3: 0.9, typical_cycle: 5 },
  { number: 1, confirmation_count: 0, evaluable_cases: 0, rate_within_3: null, typical_cycle: null },
];

const sorted = sortSignalsForDisplay(items);
assert(
  sorted.map((s) => s.number).join(",") === "7,2,4,9,1",
  `unexpected order: ${sorted.map((s) => s.number)}`,
);
assert(compareSignalsForDisplay(items[0], items[1]) > 0, "higher confirmations first");
assert(compareSignalsForDisplay(items[4], items[0]) > 0, "zero evidence last");

console.log("signal-order.node-test.mts OK");
