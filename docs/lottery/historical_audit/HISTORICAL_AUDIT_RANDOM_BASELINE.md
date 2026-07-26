# Historical Audit — Random / base baselines

Window: **next_calendar_day**  
Definition: hit iff prediction ∩ next-day FEATURED numbers ≠ ∅.  
Denom: cases with fuerte and next-day draws present = **2072** (1 case excluded: no next-day draws).  
Seed: `20260726`.

## Results

| Strategy | hits | denom | hit_rate | Wilson 95% |
|----------|-----:|------:|---------:|------------|
| Official T1×T2 | 536 | 2072 | 0.258687 | [0.24029, 0.277978] |
| Random one number | 381 | 2072 | 0.183880 | [0.16779, 0.201141] |
| Random same k | 551 | 2072 | 0.265927 | [0.247348, 0.285372] |
| T1 companions no confirmation (≤5) | 380 | 2072 | 0.183398 | [0.167325, 0.200642] |
| Direct T2 neighbors (rejected rule) | 745 | 2072 | 0.359556 | [0.339171, 0.380461] |

## Base frequency

| Quantity | Value |
|----------|------:|
| mean(\|U\|/100) next day | 0.180048 |
| avg k official | 1.6406 |
| expected random-one | 0.180048 |
| expected random-same-k | 0.277963 |

## Lifts / diffs

| Comparison | Value |
|------------|------:|
| Official / random one | **1.4068** |
| Official / random same k | **0.9728** |
| Official / T1 unconfirmed | 1.4105 |
| Official / direct T2 | 0.7195 |
| Official / base freq (random one) | 1.4368 |
| Absolute diff vs random same k | **−0.00724** |

## Interpretation

- Beating **random one** (lift ≈ 1.41) is expected when official emits \(k≈1.64\) candidates.
- Against **equal-sized random**, lift ≈ **0.97** (slightly worse). No predictive advantage after controlling for \(k\).
- Direct T2 has higher raw hit rate because it emits larger neighbor sets; it remains **rejected** as fuerte methodology (C2).
- Do **not** claim predictive value: lift vs same-k is near/below 1.

Bias control: retired scoring that only checked the official first_appearance number (that inflated lift to ~40×).
