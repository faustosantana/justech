# RETENCIONES-1 — Resumen Ejecutivo

**Objetivo:** convertir pagos y retenciones fiscales dominicanas en un módulo oficial Justech
reutilizable e integrarlo al catálogo de licencias.

**Nombre visible:** Pagos y Retenciones Dominicanas · **Código:** `payments_withholding_rd`
**Módulo técnico:** `justech_l10n_do_payments_withholding`

---

## Qué se hizo (sin tocar PROD, sin commit/push/merge)

1. **Auditoría read-only** del motor de retenciones (código + TEST).
2. **Módulo Justech creado** (Etapa A, no destructiva): empaqueta la funcionalidad y la publica
   en el catálogo comercial sin mover la lógica existente.
3. **Integración al catálogo** validada en TEST: aparece en Crear Licencia, Licencias y
   Personalizaciones, y Módulos del Cliente; **10 interruptores ON/OFF** comerciales.
4. **Validación funcional en TEST** de los 14 casos + flujo E2E (con rollback) + **healthcheck PASS**.
5. **Entregables** en `evidence/retenciones-1/`.

## Estado actual

| Elemento | Estado |
|---|---|
| Motor de retenciones (`hellenia_account`) | Intacto (no modificado) |
| Módulo `justech_l10n_do_payments_withholding` | Creado + instalado en TEST |
| Catálogo (`payments_withholding_rd`) | Integrado y visible en TEST |
| Switches comerciales | 10, en PAGOS / RETENCIONES / DOCUMENTOS |
| 6 personalizaciones previas | Intactas (sin regresión) |
| Healthcheck TEST | PASS |
| PROD | Sin cambios |
| Git | Sin commit / push / merge |

## Recomendación

- **Desplegar a PROD:** todavía **no**. La Etapa A es segura, pero recomendamos desplegar solo
  tras aprobación explícita y una ventana con backup. La **Etapa B** (reubicación física del motor)
  debe ejecutarse por PRs pequeños con validación TEST antes de PROD.
- **Higiene de datos:** depurar los duplicados `RET-NONE` del catálogo (1 032 registros) en una
  tarea aparte (no bloqueante).

## Entregables

- `RETENCIONES_AUDIT_REPORT.md`
- `RETENCIONES_ARCHITECTURE.md`
- `RETENCIONES_MIGRATION_PLAN.md`
- `RETENCIONES_TEST_VALIDATION.json`
- `RETENCIONES_RISKS.md`
- `RETENCIONES_SUMMARY.md`
