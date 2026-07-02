# Deuda Técnica Final — Fase 11

**Cliente:** Hellenia, S.R.L.  
**Producto:** Justech l10n DO MVP v19.0.1.1.0  
**Fecha:** 2026-06-30  
**Actualización:** Post Sprint 0 + UAT + Fase 11

---

## 1. Resumen ejecutivo

| Severidad | Abiertos | Cerrados Sprint 0 | Esfuerzo restante |
|-----------|:--------:|:-----------------:|-------------------|
| P0 | **0** | 4 | — |
| P1 | 8 | 0 | 2-3 semanas dev |
| P2 | 10 | 0 | Backlog |
| P3 | 6 | 0 | Oportunista |
| **Total** | **24** | **4** | |

**Nivel global deuda:** **MEDIA-BAJA** (P0 cerrados; P1 no bloquean Go-Live Hellenia)

---

## 2. P0 — Crítico

| ID | Deuda | Estado Fase 11 | Cierre |
|----|-------|----------------|--------|
| TD-001 | Sin `ir.rule` multi-empresa | ✅ **CERRADO** | Sprint 0 |
| TD-002 | Race condition `consume_next` | ✅ **CERRADO** | Sprint 0 |
| TD-003 | `action_void_ncf` sin check servidor | ✅ **CERRADO** | Sprint 0 |
| TD-004 | Sin constraint SQL unique NCF | ✅ **CERRADO** | Sprint 0 |

---

## 3. P1 — Alto

| ID | Deuda | Módulo | Impacto | Riesgo | Complejidad | Tiempo est. | Prioridad |
|----|-------|--------|---------|--------|-------------|-------------|-----------|
| TD-005 | `_sql_constraints` → `models.Constraint` | base, ncf | Upgrade Odoo 20 | Medio | Baja | 4h | P1 |
| TD-006 | Hardcoded `env.ref(doc_type_b*)` | ncf | Mantenibilidad | Bajo | Media | 6h | P1 |
| TD-007 | `parse_ncf` sin ValueError handling | base, ncf | Crash edge case | Medio | Baja | 2h | P1 |
| TD-008 | ITBIS por nombre impuesto | reports | Reporte incorrecto si renombran tax | Medio | Media | 8h | P1 |
| TD-009 | Sin i18n `es_DO.po` | todos | UX comercial | Medio | Media | 16h | P1 |
| TD-010 | Cobertura tests ~50% | tests | Regresiones | Medio | Alta | 24h | P1 |
| TD-011 | B03 sin prueba unitaria dedicada | ncf | Regresión ND | Bajo | Baja | 4h | P1 |
| TD-012 | `in_refund` sin lógica NCF | ncf | Gap fiscal compras | Medio | Media | 12h | P1 |

---

## 4. P2 — Medio

| ID | Deuda | Impacto | Riesgo | Complejidad | Tiempo | Prioridad |
|----|-------|---------|--------|-------------|--------|-----------|
| TD-013 | `justech_do_ncf_alert_days` sin usar | Bajo | Bajo | Baja | 4h | P2 |
| TD-014 | `authorization_number` sin validar | Medio | Bajo | Baja | 2h | P2 |
| TD-015 | `void_reason` histórico opcional drafts | Bajo | Bajo | Baja | 1h | P2 |
| TD-016 | Sin `mail.thread` rangos | Auditoría | Bajo | Media | 6h | P2 |
| TD-017 | `_find_active_range` filter Python | Performance | Bajo | Media | 4h | P2 |
| TD-018 | Reporte 608 dominio fecha | Reporte | Bajo | Baja | 2h | P2 |
| TD-019 | Sin cron marcar rangos expired | Operación | Medio | Baja | 4h | P2 |
| TD-020 | RNC sin dígito verificador DGII | Calidad datos | Medio | Media | 8h | P2 |
| TD-021 | Branding hellenia en manifests | Producto | Bajo | Baja | 2h | P2 |
| TD-022 | Tests `assertRaises(Exception)` | Calidad tests | Bajo | Baja | 2h | P2 |

---

## 5. P3 — Bajo

| ID | Deuda | Tiempo est. |
|----|-------|-------------|
| TD-023 | Sin `static/description` Apps | 8h |
| TD-024 | Sin type hints | Oportunista |
| TD-025 | Docstrings incompletos | 8h |
| TD-026 | Duplicación setup tests | 4h |
| TD-027 | Export XLSX sin límite memoria | 6h |
| TD-028 | Sin CHANGELOG por módulo | 2h |

---

## 6. Deuda operativa (no código)

| ID | Deuda | Prioridad | Bloquea Go-Live |
|----|-------|-----------|-----------------|
| OP-01 | Stack prod no desplegado | P0 | Sí |
| OP-02 | Router Traefik prod | P0 | Sí |
| OP-03 | SMTP | P0 | Recomendado |
| OP-04 | Usuarios funcionales | P0 | Sí |
| OP-05 | Rangos NCF DGII | P0 | Sí |
| OP-06 | Monitoreo alertas | P1 | No |
| OP-07 | Docs Fase 5 obsoletos | P2 | No |
| OP-08 | Módulos esqueleto en repo | P2 | No |

---

## 7. Deuda intencional (fuera MVP)

| Item | Fase futura | Complejidad |
|------|-------------|-------------|
| eNCF serie E | v2.0 | Muy alta |
| Formato TXT DGII oficial | v1.1 | Alta |
| Web Services DGII | v2.0 | Muy alta |
| POS fiscal | v1.2+ | Alta |
| Infile | v2.0+ | Muy alta |
| IT-1 / 609 / IR-17 | v1.2 | Media-Alta |

---

## 8. Criterio de cierre deuda

| Meta | Estado |
|------|--------|
| P0 código cerrados | ✅ |
| Cobertura ≥65% | ❌ (~50%) |
| Record rules en CI | ⚠️ Manual |
| Test concurrencia PASS | ✅ |
| i18n es_DO | ❌ |

**Deuda para comercialización plena:** cerrar P1 + formato DGII + manuales.

---

## 9. Certificación bloque 9

| Clasificación | **PASS CON OBSERVACIONES** |
|---------------|---------------------------|
| Bloqueante Go-Live código | **No** |
| Bloqueante comercialización | **Sí** (P1 + docs comerciales) |

---

**Sin modificaciones de código en Fase 11.**
