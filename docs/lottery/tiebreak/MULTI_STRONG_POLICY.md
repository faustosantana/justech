# Política Multi-Fuerte

## Principio

No fingir precisión cuando la evidencia no distingue candidatos.

## Estados de clasificación

| Clasificación | Cuándo |
|---------------|--------|
| `FUERTE_PRINCIPAL` | Desempate sólido (clave socio estrictamente mejor) |
| `FUERTE_SECUNDARIO` | Segundo en ranking tras desempate resuelto |
| `EMPATE_MULTI_FUERTE` | Claves socio idénticas tras umbral |

## Campos de resultado

- `confidence_margin` / `decision_margin`
- `tie_status` = `unresolved_multi`
- `unresolved_tie` = true
- `shared_rank` = 1 para peers empatados
- `multi_fuerte_numbers` en payload `tiebreak`
- `multi_fuerte_peers` en `primary_signal`

## Ejemplo (44, 63)

- 22 — `EMPATE_MULTI_FUERTE`
- 70 — `EMPATE_MULTI_FUERTE`

Ambos conservan score 174; ninguno se declara único fuerte.

## Ejemplo resuelto (49, 44, 70)

- 35 — `FUERTE_PRINCIPAL`
- 22 — permanece en candidatos (secundario / familia según score)
