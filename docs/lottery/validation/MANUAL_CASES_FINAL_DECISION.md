# Manual Cases — Final Decision

## Per-case final status

| Caso | Manual | Oficial (T1×T2) | Clasificación final | Histórico |
|------|--------|-----------------|---------------------|-----------|
| C1 | 29 | 29 | **FUERTE OFICIAL** | OK (nota: DB Nacional≠41 ese día; GM=41) |
| C2 | 75 | ∅ | **DIRECT_T2_NEIGHBOR_SIGNAL** (62→75) | Pattern backtest **RECHAZADO** vs random |
| C3 | 35 | {22, 35} | **FUERTE OFICIAL** (no singleton) | OK |
| C4 | 54 | 54 | **FUERTE OFICIAL** | Día+1 Loteka 54 ✓ |
| C5 | 54 | 54 | **FUERTE OFICIAL** | Día+1 **Gana Mas** 54 ✓ (DEV sync) |

## Decisions

1. **Methodology `nr-historical-relations-j1.0.0` remains the only official strengthening rule.**
2. **C2 is permanently labeled secondary T2 signal in the Lab** — never shown as fuerte oficial.
3. **C2 pattern is statistically rejected** as a predictive upgrade (lift ≈ 1.01).
4. **No motor / table / formula changes.**
5. **C5 closed** with DEV incremental sync evidence.

## Ready for J-11A?

Yes, with the explicit observation that C2 remains an experimental *label* in the UI for educational clarity, not a methodology extension.

See `PHASE_PRE_J11A_VALIDATION_CLOSURE_REPORT.md`.
