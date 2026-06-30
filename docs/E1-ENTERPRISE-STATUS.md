# Estado Fase E1 — Enterprise DEV

**Fecha:** 2026-06-30  
**Estrategia:** **Portal Odoo (descarga oficial)** como vía principal; GitHub en paralelo  
**E1a:** ⏳ Pendiente — entrega archivo/URL a Cursor + aprobación explícita

---

## Cambio de estrategia (2026-06-30)

| Vía | Estado |
|-----|--------|
| GitHub `odoo/enterprise` | ❌ `faustosantana` sin acceso repo (SSH OK) |
| **Portal Odoo Sources** | ✅ **Preparado** — ver [E0.6b](E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md) |
| **Entrega semi-automática** | ✅ [E0.6c](E0.6c-ENTERPRISE-DELIVERY-FLOW.md) |
| Comparativa completa | [ENTERPRISE_ACCESS_OPTIONS.md](ENTERPRISE_ACCESS_OPTIONS.md) |

**No bloquear proyecto** esperando GitHub.

---

## Verificación VPS — descarga automática

| Resultado | Detalle |
|-----------|---------|
| ❌ URL Enterprise permanente | Requiere sesión odoo.com — no hay wget público |
| ✅ Semi-automático | URL temporal del navegador → `download-enterprise-portal.sh` |
| ✅ Sin SCP usuario | Archivo adjunto → `receive-enterprise-archive.sh` |

---

## Completado (sin código Enterprise)

| Área | Estado |
|------|--------|
| Arquitectura congelada | ✅ |
| Validación exhaustiva Python + bash | ✅ `validate_enterprise_archive.py` |
| Scripts: `download-enterprise-portal.sh`, `receive-enterprise-archive.sh`, `e1a-portal-pipeline.sh` | ✅ |
| Scripts: `extract-enterprise-portal.sh`, `validate-enterprise-archive.sh` | ✅ |
| `downloads/enterprise/` staging | ✅ |
| Documentación acceso + entrega | ✅ |
| l10n RD análisis | ✅ [L10N-RD-READINESS.md](L10N-RD-READINESS.md) |
| DEV Community | ✅ Operativo |
| TEST / PROD | ✅ Sin tocar |

---

## Próximo paso (usuario)

1. **Usuario:** Verificar Download en [odoo.com/page/download](https://www.odoo.com/page/download) (Enterprise Sources 19)
2. **Usuario:** Entregar **URL temporal** o **archivo adjunto** a Cursor ([E0.6c](E0.6c-ENTERPRISE-DELIVERY-FLOW.md)) — **sin tocar VPS**
3. **Cursor:** `e1a-portal-pipeline.sh --validate-only`
4. **Usuario:** *"Aprobado E1a portal"* cuando quiera instalar en DEV
5. **Cursor:** `e1a-portal-pipeline.sh --execute`

---

## No ejecutado

- ⛔ Extract tarball / `web_enterprise`
- ⛔ E1b licencia
- ⛔ E1c l10n
- ⛔ Wizard / usuarios
- ⛔ Producción
