# Deuda Técnica — Justech l10n DO MVP

**Fecha inventario:** 2026-06-30  
**Origen:** Fase 6.5 Auditoría  
**Nivel global:** **MEDIA**

---

## Resumen por severidad

| Severidad | Items | Esfuerzo estimado |
|-----------|-------|-------------------|
| P0 — Crítico | 4 | Sprint hardening |
| P1 — Alto | 8 | 1-2 sprints |
| P2 — Medio | 10 | Backlog |
| P3 — Bajo | 6 | Oportunista |

---

## P0 — Crítico (bloqueante TEST/producción)

| ID | Deuda | Módulo | Impacto |
|----|-------|--------|---------|
| TD-001 | Sin `ir.rule` multi-empresa | todos | Fuga datos entre compañías |
| TD-002 | Race condition `consume_next` | ncf | NCF duplicados en concurrencia |
| TD-003 | `action_void_ncf` sin check grupo servidor | ncf | Bypass seguridad RPC |
| TD-004 | Sin constraint SQL unique NCF posted | ncf | Duplicado bajo fallo constraint Python |

---

## P1 — Alto

| ID | Deuda | Módulo |
|----|-------|--------|
| TD-005 | `_sql_constraints` deprecado Odoo 19 | base, ncf |
| TD-006 | Hardcoded `env.ref(doc_type_b*)` | ncf |
| TD-007 | `parse_ncf` sin manejo ValueError | base, ncf |
| TD-008 | Reportes ITBIS por nombre impuesto | reports |
| TD-009 | Sin i18n (`i18n/es_DO.po`) | todos |
| TD-010 | Cobertura tests ~48% | tests |
| TD-011 | B03 sin prueba E2E | ncf |
| TD-012 | `in_refund` sin lógica NCF | ncf |

---

## P2 — Medio

| ID | Deuda | Módulo |
|----|-------|--------|
| TD-013 | Campo `justech_do_ncf_alert_days` sin usar | base |
| TD-014 | `authorization_number` sin validar | ncf |
| TD-015 | `void_reason` opcional | ncf |
| TD-016 | Sin `mail.thread` auditoría rangos | ncf |
| TD-017 | `_find_active_range` filter Python | ncf |
| TD-018 | Reporte 608 dominio fecha inconsistente | reports |
| TD-019 | Sin cron marcar rangos expired | ncf |
| TD-020 | RNC sin dígito verificador DGII | base |
| TD-021 | Branding hellenia en manifests | todos |
| TD-022 | Tests `assertRaises(Exception)` genérico | tests |

---

## P3 — Bajo

| ID | Deuda | Módulo |
|----|-------|--------|
| TD-023 | Sin `static/description` Apps | todos |
| TD-024 | Sin type hints | todos |
| TD-025 | Docstrings incompletos | todos |
| TD-026 | Duplicación setup tests | tests |
| TD-027 | Export XLSX sin límite memoria | reports |
| TD-028 | Sin CHANGELOG por módulo | docs |

---

## Deuda intencional (MVP scope)

| Item | Razón | Fase futura |
|------|-------|-------------|
| eNCF serie E | Fuera alcance | Fase 8+ |
| Formato TXT DGII | MVP básico | `justech_l10n_do_dgii` |
| Web Services DGII | Fuera alcance | Fase DGII |
| POS | No iniciar | `justech_l10n_do_pos` |
| Infile | Fuera alcance | Fase Infile |

---

## Métricas de deuda

```
Deuda P0:     4 items  ████░░░░░░  Crítica
Deuda P1:     8 items  ████████░░  Alta
Deuda P2:    10 items  ██████████  Media
Deuda P3:     6 items  ██████░░░░  Baja
─────────────────────────────────
TOTAL:       28 items registrados
```

---

## Criterio de cierre

La deuda se considera **BAJA** cuando:
- [ ] TD-001 a TD-004 resueltos
- [ ] Cobertura ≥65%
- [ ] Record rules en CI test
- [ ] Test concurrencia NCF PASS

Hasta entonces: **DEUDA MEDIA**
