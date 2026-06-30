# Estado Fase E1 — Enterprise DEV

**Fecha:** 2026-06-30  
**Estado:** Documentación revisada — **E1 NO ejecutado** — esperando aprobación E1a

---

## Completado (E0.5 – E0.9 + revisión)

| Fase | Estado | Evidencia |
|------|--------|-----------|
| E0.5 Licenciamiento oficial | ✅ Corregido | `ENTERPRISE-LICENSING.md` |
| E0.6 GitHub SSH | ✅ Actualizado | `E0.6-GITHUB-ENTERPRISE.md` — sin PAT permanente |
| E0.7 Arquitectura permanente | ✅ | `ARCHITECTURE.md` — DEV→TEST→PROD |
| E0.8 Custom skeleton | ✅ | `hellenia_*`, `justech_core` |
| E0.9 Git strategy | ✅ | `GIT-STRATEGY.md` |
| Upgrade path 20+ | ✅ | `UPGRADE-PATH.md` |
| E1 validación final | ✅ | `E1-CHECKLIST.md` revisado |

---

## Cambios respecto a versión anterior

| Tema | Antes | Ahora |
|------|-------|-------|
| Licenciamiento | Asumía 1 BD total sin matices | Citas oficiales + duplicación neutralizada |
| GitHub VPS | PAT en `github.env` | **SSH key dedicada** (PAT solo fallback) |
| Enterprise | ZIP mencionado como alternativa | **Solo repo Git oficial** |
| Arquitectura | Parcialmente temporal | **DEV→TEST→PROD permanente** |
| Custom | Solo README | **6 módulos esqueleto** |

---

## Siguiente paso

Revisar y aprobar **`docs/E1-CHECKLIST.md`** (E1a).

El usuario:
1. Vincula GitHub en portal Odoo
2. Agrega SSH public key cuando Cursor la genere

Cursor ejecuta E1a por SSH. **No editar archivos manualmente en VPS.**

---

## No ejecutado

- ⛔ Clone Enterprise
- ⛔ `web_enterprise`
- ⛔ Registro licencia
- ⛔ Wizard / usuarios / l10n / Infile
- ⛔ Producción
