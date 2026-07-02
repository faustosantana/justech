# Fase 6.5 — Actualización de Certificación (post Sprint 0)

**Fecha certificación:** 2026-06-30  
**Ambiente validado:** DEV (`hellenia_dev`)  
**Versión:** `19.0.1.1.0`  
**Rama:** `feature/justech-l10n-do-mvp`  
**Backup referencia:** `backups/dev/2026-06-30_1210`

---

## 1. Estado P0 — Cierre

| ID | Hallazgo Fase 6.5 | Estado Sprint 0 | Evidencia |
|----|-------------------|-----------------|-----------|
| TD-001 | Sin `ir.rule` multiempresa | ✅ **CERRADO** | Rules en base, ncf, reports + tests hardening |
| TD-002 | Race condition `consume_next` | ✅ **CERRADO** | Advisory lock + `FOR UPDATE` + test concurrencia PASS |
| TD-003 | `action_void_ncf` sin check servidor | ✅ **CERRADO** | `AccessError` manager + auditoría void + tests |
| TD-004 | Sin constraint SQL NCF único | ✅ **CERRADO** | Índice `account_move_justech_do_ncf_company_uniq` en DEV |

**P0 abiertos:** **0 / 4**

---

## 2. Certificación anterior vs actual

| Criterio | Fase 6.5 (pre-Sprint 0) | Post-Sprint 0 |
|----------|-------------------------|---------------|
| Producto comercial | ❌ NO | ❌ NO (deuda P1 pendiente) |
| Bloqueante TEST | ❌ 4 P0 abiertos | ✅ P0 cerrados |
| Seguridad multiempresa | ❌ Sin rules | ✅ Rules activas |
| Concurrencia NCF | ❌ Riesgo duplicado | ✅ Serialización verificada |
| Void NCF | ⚠️ Solo UI | ✅ Servidor + auditoría |
| Integridad NCF | ⚠️ Solo Python | ✅ Python + índice PostgreSQL |
| Tests unitarios | 13 | **19** |
| E2E PHASE6_MVP | ✅ (pre-P0) | ✅ Re-validado post-P0 |

---

## 3. Validación reproducible

```bash
# En VPS DEV (/opt/odoo-projects/hellenia)
./scripts/upgrade-phase6-mvp-module.sh dev    # → 19/19 tests
./scripts/test-ncf-concurrency.sh dev       # → PASS
./scripts/validate-phase6-mvp.sh dev          # → PHASE6_MVP ok: true
```

---

## 4. Veredicto de promoción

| Pregunta | Respuesta |
|----------|-----------|
| ¿P0 cerrados? | **Sí** — los 4 ítems bloqueantes están resueltos en DEV |
| ¿MVP puede pasar a TEST? | **Sí** — autorizado promover a TEST |
| ¿MVP listo para producción/POS? | **No** — requiere validación en TEST, deuda P1 y gate comercial |
| ¿Producto comercial? | **No** — i18n, cobertura ≥75%, formato DGII oficial siguen en backlog |

---

## 5. Condiciones para TEST

1. Backup TEST antes de deploy (no ejecutado en este sprint).
2. Deploy rama `feature/justech-l10n-do-mvp` en ambiente TEST.
3. Re-ejecutar `upgrade-phase6-mvp-module.sh test` y `validate-phase6-mvp.sh test`.
4. No instalar POS hasta cierre explícito de fase POS.

---

## 6. Referencias

- [SPRINT0_HARDENING_REPORT.md](SPRINT0_HARDENING_REPORT.md) — detalle técnico Sprint 0
- [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md) — deuda P1–P3
- [PHASE65_SECURITY_REVIEW.md](PHASE65_SECURITY_REVIEW.md) — auditoría original (supersedida en P0 por este documento)
- [PHASE6_TEST_RESULTS.md](PHASE6_TEST_RESULTS.md) — resultados Fase 6 (actualizar tras TEST)

---

## 7. Firma de certificación

```
CERTIFICACIÓN: JUSTECH L10N DO MVP — POST SPRINT 0 HARDENING
Estado P0:        CERRADO (4/4)
PHASE6_MVP DEV:   ok: true
Concurrencia NCF: PASS
Promoción TEST:   AUTORIZADA
Producto comercial: NO (pendiente P1+)
Fecha:            2026-06-30
```
