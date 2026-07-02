# Paridad TEST vs PROD — Antes de promoción

**Fecha:** 2026-07-01  
**Estado:** Sin diferencias bloqueantes  
**Evidencia:** `evidence/test-prod-parity-before-promotion.json`

## Módulos comparados

| Módulo | TEST | PROD |
|--------|------|------|
| hellenia_account | 19.0.1.0.13* | 19.0.1.0.13 |
| hellenia_ui | 19.0.1.0.4 | 19.0.1.0.4 |
| hellenia_ux | 19.0.1.0.0 | 19.0.1.0.0 |
| account_accountant | 19.0.1.1 | 19.0.1.1 |
| account_reports | 19.0.1.0 | 19.0.1.0 |
| justech_l10n_do_reports | 19.0.1.11.0 | 19.0.1.11.0 |

\* TEST actualizado a **19.0.1.0.14** durante certificación 18.10B. PROD permanece en 19.0.1.0.13 hasta promoción aprobada.

## Menús contables críticos

| Menú | TEST | PROD |
|------|------|------|
| Asientos contables (`account.menu_action_account_moves_all`) | activo | activo |
| Apuntes contables (`account.menu_action_move_journal_line_form`) | activo | activo |

## Diferencias

Ninguna diferencia bloqueante detectada en módulos ni menús críticos.

## Riesgo promoción

- TEST tiene `hellenia_account` 19.0.1.0.14; PROD aún no.
- Promoción debe incluir upgrade módulo + reinicio workers.
- **NO promover** sin aprobación explícita.

## Grupo it@justech.do

No encontrado por nombre en shell; verificar manualmente permisos antes de promoción.
