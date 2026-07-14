# Release candidata — Compras fiscal recibidos/emitidos

## Módulos
| Módulo | Versión |
|---|---|
| `justech_l10n_do_base` | 19.0.1.24.0 |
| `justech_l10n_do_ncf` | 19.0.2.8.0 |

## Contenido
- Separación UI/motor: Documento recibido (LATAM) vs Comprobante emitido (Justech B11/B13/B17).
- Configs `justech.do.purchase.emission.config` (12 = 4×3), idempotente vía post-migrate.
- Sin rangos ficticios; emisión solo con rango activo.

## Continuidad obligatoria
- JUSTECH B11: 11–15 → próximo B1100000011
- JUSTECH B13: 213–217 → próximo B1300000213
- B17 y demás empresas: config sin rango, inactivo
