# Walk-forward (fuera de muestra)

Partición temporal: entrenar años previos → validar año siguiente.

| Train | Test | In-sample HR | OOS HR | Δ pp |
|-------|------|-------------:|-------:|-----:|
| [2022] | 2023 | 0.2625 | 0.251185 | -1.132 |
| [2022, 2023] | 2024 | 0.254296 | 0.298507 | 4.421 |
| [2022, 2023, 2024] | 2025 | 0.272358 | 0.283505 | 1.115 |
| [2022, 2023, 2024, 2025] | 2026 | 0.27551 | 0.33945 | 6.394 |

Una relación/regla no se declara validada solo por desempeño in-sample.
