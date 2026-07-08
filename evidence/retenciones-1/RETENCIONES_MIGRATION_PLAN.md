# RETENCIONES-1 — Plan de Migración / Compatibilidad

**Principio rector:** no dañar Hellenia (entregada al cliente), no cambiar PROD,
no tocar NCF/DGII/COA/impuestos/secuencias/datos, migración controlada.

---

## Etapa A — Empaquetado (SIN migración de datos) — IMPLEMENTADA/TEST

- Añade un módulo nuevo que **solo suma** una entrada al catálogo y switches comerciales.
- **No** cambia modelos, campos, vistas, XML IDs ni impuestos existentes.
- **No** requiere migración de datos.
- Reversible: `desinstalar justech_l10n_do_payments_withholding` restaura el estado anterior
  (los 6 items previos del catálogo permanecen intactos — validado en TEST).

### Compatibilidad garantizada (Etapa A)
| Riesgo | Mitigación |
|---|---|
| Duplicar campos | No se crea ningún campo nuevo en `account.*` |
| Duplicar menús | No se crea menú nuevo (reutiliza el del catálogo) |
| Cambiar XML IDs | No se toca ningún XML ID existente |
| Romper vistas | No se hereda ninguna vista de retención |
| Romper 623 | No se toca `justech_l10n_do_reports` |

---

## Etapa B — Reubicación física del motor (PROPUESTA — requiere aprobación)

Objetivo: que los modelos/vistas/reportes de retención residan en
`justech_l10n_do_payments_withholding` en lugar de `hellenia_account`.

### B.1 Reglas de compatibilidad
1. **Mantener los nombres de modelo** `hellenia.withholding.catalog`,
   `hellenia.payment.withholding.line`, `hellenia.payment.application.line`
   (renombrarlos rompería datos y referencias — NO se hace).
2. **Preservar XML IDs** de vistas/acciones/menús. Si un XML ID debe cambiar de módulo,
   re-parentear vía `ir.model.data` (UPDATE `module`) en un script de migración, **no** borrar+crear.
3. **Preservar tablas y columnas** (mismos `_name` ⇒ mismas tablas). Cero pérdida de datos.
4. **No tocar** impuestos l10n_do, secuencias NCF, COA ni datos del cliente.

### B.2 Secuencia de traslado (por PRs pequeños, cada uno probado en TEST)
1. **PR-1**: mover `hellenia.withholding.catalog` + `sync_catalog_from_taxes` al nuevo módulo;
   `hellenia_account` pasa a depender de él. Migración: re-parentear XML IDs del catálogo.
2. **PR-2**: mover `hellenia.payment.withholding.line` y `hellenia.payment.application.line`.
3. **PR-3**: mover las extensiones de `account.payment` / `account.payment.register` / `account.move`.
4. **PR-4**: mover vistas y reportes (recibo de retención); re-parentear sus XML IDs.
5. **PR-5**: repuntar la dependencia de `justech_l10n_do_reports` (623) al nuevo módulo.
6. **PR-6**: `hellenia_account` queda como capa de compatibilidad (o se limpia el código muerto).

### B.3 Scripts de migración por versión (`migrations/19.0.x/pre|post-migrate.py`)
- `pre-migrate`: registrar en un dict los XML IDs a re-parentear.
- `post-migrate`: `UPDATE ir_model_data SET module='justech_l10n_do_payments_withholding'
  WHERE module='hellenia_account' AND name IN (...)`.
- Idempotente y con verificación previa de existencia.

### B.4 Rollback Etapa B
- Cada PR es reversible desinstalando el nuevo módulo y restaurando la dependencia previa,
  o restaurando backup de BD pre-migración (obligatorio antes de PROD).

---

## Orden recomendado de despliegue

1. **TEST** — Etapa A (hecho, healthcheck PASS).
2. Aprobación del cliente/Justech de la arquitectura.
3. **TEST** — Etapa B PR a PR, con healthcheck entre cada uno.
4. **PROD** — solo tras backup + validación completa + ventana aprobada.

> Nada de lo anterior se ha ejecutado en PROD. No hay commit/push/merge.
