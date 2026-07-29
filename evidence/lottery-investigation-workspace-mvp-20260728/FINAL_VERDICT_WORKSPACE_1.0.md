# Workspace 1.0 — Cierre post-fix de routing

## Causa raíz confirmada
`WorkspaceSpeechActDetector.detect` demasiado amplio + `HermesDecisionEngine.decide` priorizando `asset_action` con cualquier investigación activa (sin asset / sin verbo de tabla).

## Fix
Gate estricto: workspace solo con `active_asset` válido + acto claro, o boot explícito show/export/tabla. Bloqueo de frases factuales Analyst 2.1 (`últimas N`, `En Nacional.`, `Ahora en todas…`, `¿Solo en 2026?`, etc.).

## Resultados
| Suite | Resultado |
|-------|-----------|
| Unit residuals + positivos | 9/9 |
| Residuales Cert (T07–T10, G03.T03, G20.T07) | 6/6 PASS |
| WORKSPACE_ACTIONS_40 | 40/0 |
| Agent50 | 50/0 |
| Manual30 | 30/0 |
| Official Scope | 18 passed |
| Cert200 | 200/0 CERTIFIED, http_500=0 |
| API E2E show→filter→sort→export | PASS (122→28, xlsx 28 filas) |

## Veredicto
**LISTO PARA BETA WORKSPACE**
