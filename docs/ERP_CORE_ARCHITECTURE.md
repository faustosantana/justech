# Justech ERP — Core Architecture

**Versión:** 2.0 · **Fase 31 replanteada** · Clasificación oficial de módulos

---

## Cambio v2.0 — Capa plataforma primero

Antes de clasificar módulos funcionales, existe la **Plataforma Justech**:

| Capa | Módulos | Categoría nueva |
|------|---------|-----------------|
| **PLATAFORMA** | justech_modules, hellenia_governance, justech_admin | Obligatorios producto |
| **CORE JUSTECH** | justech_l10n_do_base, justech_l10n_do_ncf, … | Fiscal RD |
| **LICENCIABLE** | reports, design, pos, … | Add-ons |
| **LEGACY** | hellenia_* | Migrar post-plataforma |

Ver: `ERP_PLATFORM_ARCHITECTURE.md`

---

## Leyenda categorías

| Categoría | Significado |
|-----------|-------------|
| **PLATAFORMA** | Infraestructura producto — construir primero (F31) |
| **CORE** | Odoo Enterprise requerido |
| **CORE JUSTECH** | Obligatorio despliegue Justech ERP RD |
| **LICENCIABLE** | Activable vía justech_modules |
| **LEGACY→MIGRAR** | Existe; migrar post F31 |
| **EXCLUIDO** | No SKU comercial |

---

## Plataforma Justech (F31 — prioridad absoluta)

| Módulo | Categoría | Sprint | Obligatorio | Depende de | Responsabilidad |
|--------|-----------|--------|:-----------:|------------|-----------------|
| **justech_modules** | PLATAFORMA | F31.1 | Sí | base, mail | Licencias, features, activación |
| **hellenia_governance** | PLATAFORMA | F31.2 | Sí | justech_modules | Permisos, roles, menús, auditoría |
| **justech_admin** | PLATAFORMA | F31.3 | Sí | modules + governance | Centro de Control UI |

**Regla:** Ningún módulo funcional nuevo sin integración a los tres.

---

## Clasificación módulos existentes

| Módulo | Categoría | Obligatorio | Licenciable | Estado | Post-plataforma |
|--------|-----------|:-----------:|:-----------:|--------|-----------------|
| `account` | CORE | Sí | Odoo EE | PROD | — |
| `justech_l10n_do_base` | CORE JUSTECH | Sí (RD) | Incluido | PROD | Registrar F31.4 |
| `justech_l10n_do_ncf` | CORE JUSTECH | Sí (RD) | Incluido | PROD | Registrar F31.4 |
| **justech_withholding** | CORE JUSTECH | Sí (RD) | Incluido | **F32** | Nace con hooks plataforma |
| `justech_l10n_do_reports` | LICENCIABLE | Sí fiscal | Add-on | PROD | Desacoplar F32 |
| `justech_report_design` | LICENCIABLE | Recomendado | Add-on | PROD | Desacoplar F32 |
| `hellenia_account` | LEGACY→MIGRAR | — | — | PROD | → withholding F32 |
| `hellenia_reports` | LEGACY→DEPRECAR | No | — | PROD | F32 |
| `hellenia_ux` | LEGACY→REFACTOR | Recomendado | Add-on | PROD | F32 |
| `hellenia_ui` | LEGACY→ABSORB | No | — | PROD | → governance F31.2 |
| `hellenia_pos` | LEGACY→REFACTOR | No | Add-on | DEV | POS Enterprise F34 |
| `justech_core` | EXCLUIDO→MERGE | — | — | Skeleton | Utilidades → modules |
| `hellenia_base` | EXCLUIDO | No | — | Skeleton | Archivar |
| `hellenia_inventory` | EXCLUIDO | No | — | Skeleton | Archivar |

---

## Orden implementación oficial

```
1. justech_modules          (F31.1)
2. hellenia_governance        (F31.2)
3. justech_admin              (F31.3)
4. Integración piloto         (F31.4)
─── gate infraestructura ───
5. justech_withholding        (F32)
6. Desacoplamiento reports    (F32)
7. Arquitectura financiera    (F33)
8. POS Enterprise             (F34)
9. Marketplace                (F35)
10. IA                        (F36+ arquitectura only)
```

---

## Reglas arquitectura core v2.0

1. **PLATAFORMA** precede a todo módulo funcional nuevo.
2. Todo **LICENCIABLE** usa `require_active()` + `require_permission()`.
3. **CORE JUSTECH** no depende de `hellenia_*` (excepto transición F32 documentada).
4. **LEGACY** no recibe features nuevas — solo shims hasta migración.
5. Nuevo módulo → manifest `justech_register` + clasificación en catálogo.

---

## SKU comercial (post F31)

### Justech ERP Platform (incluido todo despliegue)

- justech_modules + hellenia_governance + justech_admin

### Justech ERP Fiscal RD — Standard

- Platform + CORE + CORE JUSTECH

### Add-ons

- DGII Pro · Report Design · POS Enterprise · API Connect

---

## Referencias

- Plataforma: `ERP_PLATFORM_ARCHITECTURE.md`
- Catálogo: `ERP_MODULE_CATALOG.md`
- Infraestructura: `ERP_INFRASTRUCTURE_ROADMAP.md`
