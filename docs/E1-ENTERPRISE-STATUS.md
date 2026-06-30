# Estado Fase E1 — Enterprise DEV

**Fecha:** 2026-06-30  
**Estrategia:** **Portal Odoo (descarga oficial)** como vía principal; GitHub en paralelo  
**E1a:** ⏳ Pendiente — esperando tarball en VPS + aprobación ejecución

---

## Cambio de estrategia (2026-06-30)

| Vía | Estado |
|-----|--------|
| GitHub `odoo/enterprise` | ❌ `faustosantana` sin acceso repo (SSH OK) |
| **Portal Odoo Sources** | ✅ **Preparado** — ver [E0.6b](E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md) |
| Comparativa completa | [ENTERPRISE_ACCESS_OPTIONS.md](ENTERPRISE_ACCESS_OPTIONS.md) |

**No bloquear proyecto** esperando GitHub.

---

## Completado (sin código Enterprise)

| Área | Estado |
|------|--------|
| Arquitectura congelada | ✅ |
| Scripts portal: `extract-enterprise-portal.sh`, `fetch-enterprise.sh`, `validate-enterprise-archive.sh` | ✅ |
| `downloads/enterprise/` staging | ✅ |
| Documentación acceso Enterprise | ✅ |
| l10n RD análisis | ✅ [L10N-RD-READINESS.md](L10N-RD-READINESS.md) |
| DEV Community | ✅ Operativo |
| TEST / PROD | ✅ Sin tocar |

---

## Próximo paso (usuario + aprobación)

1. **Usuario:** Verificar Download en [odoo.com/page/download](https://www.odoo.com/page/download) (Enterprise Sources 19)
2. **Usuario:** Subir `.tar.gz` a `/opt/odoo-projects/hellenia/downloads/enterprise/`
3. **Usuario:** Aprobar ejecución E1a-revised
4. **Cursor:** `validate-enterprise-archive.sh` → `extract-enterprise-portal.sh` → `web_enterprise` → validar

---

## No ejecutado

- ⛔ Extract tarball / `web_enterprise`
- ⛔ E1b licencia
- ⛔ E1c l10n
- ⛔ Wizard / usuarios
- ⛔ Producción
