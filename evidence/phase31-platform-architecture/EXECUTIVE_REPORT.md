# Fase 31 Replanteada — Arquitectura Definitiva de Plataforma

**Fecha:** 2026-07-05 · **Versión:** 2.0 · **Modo:** Read-only

---

## Decisión estratégica

**Infraestructura primero. Funcionalidad después.**

El plan F31 v1.0 (desacoplamiento fiscal primero) queda **obsoleto**. La secuencia oficial es:

1. `justech_modules` — licencias
2. `hellenia_governance` — permisos (sin licencias)
3. `justech_admin` — Centro de Control (sin lógica negocio)
4. Desacoplamiento core — **solo post Gate F31**
5. Arquitectura financiera → POS → Marketplace → IA (arquitectura preparada)

---

## Validación arquitectónica (10 preguntas)

| # | Pregunta | Respuesta |
|---|----------|-----------|
| 1 | ¿Separación modules / governance / admin correcta? | **Sí** — tres preguntas distintas, tres módulos |
| 2 | ¿Duplicaciones? | **Resueltas v2.0** — governance sin licencias; admin sin modelos negocio |
| 3 | ¿Qué vive en cada módulo? | Ver matriz `ERP_PLATFORM_ARCHITECTURE.md` §3 |
| 4 | ¿APIs públicas? | modules: 4 métodos · governance: 6 métodos · admin: ninguna |
| 5 | ¿Dependencias circulares? | **Evitadas** — DAG: modules → governance → admin |
| 6 | ¿Registro automático módulos? | Manifest `justech_register` + post_init hook |
| 7 | ¿Localizaciones futuras? | `justech.localization` en modules |
| 8 | ¿Países futuros? | Feature licenciable por país + namespace `justech_l10n_XX` |
| 9 | ¿Licencias futuras? | Tiers extensibles en justech_modules |
| 10 | ¿Qué cambiar antes de código? | **Aprobar esta arquitectura v2.0** |

---

## Próximo paso

**Aprobar arquitectura** → **Sprint F31.1 justech_modules** en DEV (120h · 3 semanas)

---

## Entregables documentación

| Documento | Estado |
|-----------|--------|
| ERP_PRODUCTIZATION_PLAN.md v2.0 | ✅ |
| ERP_PLATFORM_ARCHITECTURE.md | ✅ nuevo |
| JUSTECH_MODULES_ARCHITECTURE.md | ✅ nuevo |
| HELLENIA_GOVERNANCE_ARCHITECTURE.md v2.0 | ✅ actualizado |
| JUSTECH_ADMIN_ARCHITECTURE.md | ✅ nuevo |
| ERP_INFRASTRUCTURE_ROADMAP.md | ✅ nuevo |
| ERP_CORE_ARCHITECTURE.md v2.0 | ✅ |
| ERP_MODULE_CATALOG.md v2.0 | ✅ |
| ERP_ENTERPRISE_ROADMAP.md v2.0 | ✅ |

---

## Restricciones cumplidas

✅ Sin código · sin módulos · sin ambientes · sin commit/push/merge
