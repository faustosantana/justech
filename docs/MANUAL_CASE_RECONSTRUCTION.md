# Manual Case Reconstruction (no hardcode)

| Case | Inputs | Expected | Engine class |
|------|--------|----------|--------------|
| M1 | 41+41+70 | 29 | FUERTE_PRINCIPAL |
| M2 | 41+62 | 75 | VECINO_T2_DIRECTO |
| M3 | 49+44+70 | 35 (alt 22) | FUERTE_PRINCIPAL |
| M4 | 35+14 | 54 | FUERTE_PRINCIPAL |
| M5 | 39+58 | 94 | FUERTE_PRINCIPAL |

Forbidden: `if inputs == [35,14]: return 54`.
