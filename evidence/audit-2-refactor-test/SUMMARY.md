# AUDIT-2 — Justech Global Audit Log

**Fecha:** 2026-07-07  
**Ambiente:** `hellenia_test` (TEST únicamente — PROD no tocado)  
**Módulo:** `custom/justech_global_audit_log` v`19.0.1.0.0`

## Resultado

| Criterio | Estado |
|---|---|
| Odoo 19 compatible | PASS |
| Depends mínimo (`base`) | PASS |
| Reglas desactivadas por defecto | PASS |
| `account.move` / `account.payment` inactivos | PASS |
| Tests unitarios (8/8) | PASS |
| Validación funcional TEST | PASS |
| Benchmark 100 writes `res.partner` | PASS (0.019s) |
| Healthcheck TEST | PASS |

## Benchmark TEST

- **100 writes** en `res.partner` con auditoría activa
- **Tiempo:** ~0.019s
- **Modo:** post-commit en runtime; sync en tests/validación
- **account.move:** no auditado (regla inactiva)

## Configuración activada en TEST (manual)

- Política global: ON
- Reglas ON: `res.partner`, `sale.order`, `product.template`
- Reglas OFF: `account.move`, `account.payment`

## Archivos clave

- `models/audit_service.py` — motor post-commit + API bridge
- `models/audit_policy.py` / `audit_rule.py` — configuración
- `models/audit_retention.py` + cron — limpieza
- `hooks.py` — reglas seed inactivas + `justech_register`

## Recomendación PROD

**No instalar aún en PROD.**  
Instalar en PROD solo tras: piloto extendido en TEST (7 días), medición con `sale.order`/`product.template`, y activación explícita de licencia `global_audit`.
