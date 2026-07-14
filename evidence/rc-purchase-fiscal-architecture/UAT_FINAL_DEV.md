# UAT FINAL — Compras fiscal (DEV `justech_dev`)

**Fecha:** 2026-07-14  
**Commit Git:** `43aae3d8fc4d5827523d095954b4d0c1b5f0b14b`  
**Rama:** `feature/fiscal-standard-consolidation`  
**Método:** odoo shell + `SAVEPOINT` / `ROLLBACK` (0 documentos persistidos, 0 NCF netos)

## Release
| Módulo | Versión DEV | Versión PROD (sin tocar) |
|---|---|---|
| justech_l10n_do_base | 19.0.1.24.0 | 19.0.1.23.0 |
| justech_l10n_do_ncf | 19.0.2.8.0 | 19.0.2.7.0 |

Configs: **12/12** idempotentes (`ensure_configs` + post-migrate).

## Resultados UAT
- Recibidos E31/B01/B14/B15/B16/E34: PASS (sin Justech NCF, sin consumo)
- Emitidos B11→B1100000011 / B13→B1300000213 en txn + rollback: PASS
- B17 + Omni/JustOffice/PlugSafe sin rango: bloqueo PASS
- UX clear recibidos↔emitidos: PASS
- Histórico `FP/2026/06/0033` E310000087599: PASS
- Continuidad post-UAT B11@11 B13@213: PASS
- ACL invoice RO config / no write ranges; fiscal mgr write ranges: PASS
- GL 0.00; documentos persistidos 0; rangos ficticios 0

## Producción
No deploy. Sin tabla `justech_do_purchase_emission_config`.
