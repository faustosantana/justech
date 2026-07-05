# F31.1.1 — Certificación Enterprise: Motor de Licenciamiento `justech_modules`

**Fecha:** 2026-07-05  
**Ambiente:** `hellenia_dev` (Odoo 19 Enterprise)  
**Commit:** `ac13c3b` · **API v1**  
**Sin commit / sin push / TEST-PROD intactos**

---

## Veredicto

# LICENSING ENGINE READY: **NO**

El motor es **funcional y arquitectónicamente válido** como base F31.1, pero **no está listo** para ser el único motor de licenciamiento de todo el ERP sin correcciones P1 en F31.2.

**Score ponderado:** **74.0 / 100** (umbral enterprise: 75)

---

## Resumen ejecutivo

| Área | Resultado | Notas |
|------|-----------|-------|
| Dataset escala | ✅ PASS | 500 módulos, 5.000 features, 100 compañías, 42 licencias |
| API pública v1 | ✅ PASS | 8/8 métodos validados |
| Unit tests | ✅ PASS | 20/20 |
| Multi-company | ✅ PASS | Aislamiento, max_companies, ir.rule |
| Seguridad ACL | ✅ PASS | Portal bloqueado |
| Performance | ❌ FAIL | `is_active()` ~2.3 ms/llamada (23× SLA) |
| Lifecycle expiración | ❌ FAIL | Licencia expirada no bloquea `is_active()` |
| Concurrencia UNIQUE | ❌ FAIL | Duplicado `license.company` (count=2) |
| Seguridad claves | ⚠️ ALTO | `license_key` texto plano |

---

## 1. Dataset simulado (DEV)

| Entidad | Objetivo | Real | Tiempo seed |
|---------|----------|------|-------------|
| `justech.module` | 500 | 500 | 52s (1ª corrida) |
| `justech.feature` | 5.000 | 5.000 | incluido |
| `res.company` | 100 | 100 | incluido |
| `justech.license` | mixtos | 42 | active/expired/revoked/draft |

Prefijo certificación: `cert_f311_*` — datos permanecen en DEV para auditoría.

---

## 2. API pública — resultados

| Método | Status |
|--------|--------|
| `get_api_version()` | PASS → 1 |
| `get_feature()` | PASS |
| `is_active()` | PASS (semántica parcial — ver LIFE-01) |
| `require_active()` | PASS |
| `validate_license()` | PASS |
| `check_dependencies()` | PASS |
| `activate_feature()` | PASS |
| `deactivate_feature()` | PASS |

---

## 3. Performance (10.000 iteraciones)

| Métrica | Total | Promedio | SLA | Gap |
|---------|-------|----------|-----|-----|
| `is_active()` | 23.0 s | **2.303 µs/llamada** | <100 µs | **23×** |
| `get_feature()` | 3.0 s | **300 µs/llamada** | <50 µs | **6×** |

**Causa raíz:** Sin `ormcache`; cada `is_active()` ejecuta 3–4 `search()` SQL sobre 5.000 features y licencias.

**Índices recomendados:**
- `justech_license_company(company_id, license_id)`
- `justech_feature_company(feature_id, company_id, is_active)`

**Acción F31.2 (P1):** Reintroducir cache Odoo 19 + índices compuestos.

---

## 4. Concurrencia

| Test | Resultado | Severidad |
|------|-----------|-----------|
| `license.company` UNIQUE | **FAIL** (count=2) | **crítico** |
| `feature.company` UNIQUE | PASS | — |
| `activate_feature` idempotente | PASS | — |

**CONC-01:** Segundo `create()` en par `(license_id, company_id)` no lanzó excepción.

**SQL-01:** Odoo 19 depreca `_sql_constraints`; logs DEV muestran warning en otros módulos. Verificar migración a `models.Constraint` en `justech_modules`.

---

## 5. Multi-empresa

| Test | Resultado |
|------|-----------|
| Licencia no afecta compañías no asignadas | PASS |
| `max_companies` bloquea exceso | PASS |
| `ir.rule` scope license user | PASS (0/45 visibles) |

---

## 6. Seguridad

| Test | Resultado |
|------|-----------|
| Portal no crea licencias | PASS |
| Portal no activa features | PASS |
| Claves en texto plano | CONFIRMADO (SEC-01) |
| Audit intentos inválidos | GAP (SEC-02) |

---

## 7. Lifecycle

| Estado | Resultado |
|--------|-----------|
| Activa | PASS |
| Expirada | **FAIL** (LIFE-01) |
| Revocada | PASS (`validate_license`) |
| Draft/suspendida | PASS (draft = not_active) |
| Dependencia faltante | PASS |
| Dependencia satisfecha | PASS |

### LIFE-01 (crítico)

Tras expirar la licencia, `is_active()` sigue retornando `True` porque `justech.feature.company.is_active` permanece activo y la expiración no se revalida en el path de activación operativa.

**Fix propuesto F31.2:** En `is_active()`, revalidar `expires_at` y `state` de la licencia activa antes de retornar el flag `feature.company`.

---

## 8. Rollback

| Acción | Resultado |
|--------|-----------|
| `deactivate_feature()` | PASS |
| Revocar licencia | PASS |
| Restaurar estado | Parcial — requiere nueva licencia válida |

---

## 9. Compatibilidad futura

| Sistema | Status |
|---------|--------|
| Odoo Enterprise DEV | ✅ PASS |
| Odoo Community | ⚠️ PARTIAL (validar CE 19 + privilege_id) |
| Multi-company | ✅ PASS |
| SaaS pooled | ❌ GAP (`justech.tenant`) |
| Marketplace | ❌ GAP (`module.version`) |
| `justech_admin` | ✅ READY |
| `hellenia_governance` | ✅ READY (API pública; callback F31.2) |

---

## 10. Issues clasificados

| Severidad | Código | Título |
|-----------|--------|--------|
| **crítico** | LIFE-01 | Licencia expirada no bloquea `is_active()` |
| **crítico** | CONC-01 | Duplicado `license.company` posible |
| **crítico** | SQL-01 | `_sql_constraints` → `models.Constraint` Odoo 19 |
| **alto** | PERF-01 | `is_active()` ~2.3 ms sin cache |
| **alto** | SEC-01 | `license_key` texto plano |
| **alto** | COMP-02 | `max_users` sin enforcement |
| **medio** | PERF-02 | `get_feature()` ~300 µs |
| **medio** | SEC-02 | Audit solo en validate exitoso |
| **medio** | COMP-01 | Estado `suspended` no modelado |

---

## 11. Score final

| Categoría | Score | Peso |
|-----------|-------|------|
| Arquitectura | 82 | 12 |
| API | 88 | 15 |
| Performance | 55 | 15 |
| Concurrencia | 58 | 8 |
| Multi-company | 85 | 12 |
| Seguridad | 65 | 15 |
| Lifecycle | 72 | 10 |
| Rollback | 85 | 8 |
| Escalabilidad datos | 80 | 10 |
| Future readiness | 70 | 5 |
| **TOTAL** | **74.0** | 100 |

---

## 12. Recomendaciones (sin implementar)

### P1 — Antes de `hellenia_governance`

1. **LIFE-01:** Revalidar licencia en cada `is_active()`
2. **SQL-01 / CONC-01:** Migrar constraints a `models.Constraint`
3. **PERF-01:** `ormcache` + invalidación en activate/deactivate
4. **SEC-01:** Hash `license_key` at rest
5. **COMP-02:** Enforce `max_users`

### P2 — F31.3 / SaaS

6. `justech.tenant` model
7. Audit intentos inválidos
8. Índices compuestos verificados con EXPLAIN

---

## Evidencia

```
evidence/f31-1-1-license-engine-certification/
├── TECHNICAL_REPORT.md          (este documento)
├── certification-results.json
├── certification_run.log
├── performance.csv
├── security.csv
├── concurrency.csv
├── issues.csv
├── scorecard.csv
└── recommendations.md
```

Script: `scripts/f31-1-1-license-engine-certification.py`  
Runner: `scripts/run-f31-1-1-certification-dev.sh`

---

## Conclusión

**NO** iniciar `hellenia_governance` hasta resolver **LIFE-01**, **CONC-01/SQL-01** y **PERF-01** en sprint F31.2.

El commit `ac13c3b` es una **base sólida commiteada**; la certificación enterprise confirma gaps esperables de un MVP Semana 1 ampliado con P0.
