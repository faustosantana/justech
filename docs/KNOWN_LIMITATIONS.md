# Known Limitations

- Predictions are experimental; no betting advice.
- Analytical confidence ≠ probability.
- D+1…D+7 exact rates can approach random baseline due to coverage saturation (see forensic audits).
- In-memory signal store (DEV) — not Production persistence.
- Production must not be modified/deployed from this branch without separate GO gate.
- Derivation fan-out is bounded; not an exhaustive infinite graph.
