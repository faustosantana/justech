# PERMISSIONS-UX-1 — Centro de Permisos

## Resumen

Mejora UX de la pestaña **Centro de Permisos** en Configuración → Usuarios, sin modificar grupos, ACL ni record rules.

## Resultados de validación

| Entorno | Validación funcional | Healthcheck |
|---------|---------------------|-------------|
| **TEST** (`hellenia_test`) | **PASS** — 15/15 checks | **PASS** |
| **PROD** (`hellenia_prod`) | **No ejecutado** | **No ejecutado** |

### ¿Healthcheck PASS?

**Sí, en TEST.**  
`RESULTADO: PASS` — 2026-07-07 23:25 UTC (`healthcheck-test-2026-07-07_2324.json` en VPS).

PROD no fue desplegado ni validado en esta fase.

## Evidencia generada

Directorio: `evidence/permissions-ux-1/`

| Archivo | Contenido |
|---------|-----------|
| `PERMISSIONS_UX_REPORT.md` | Este reporte |
| `PERMISSIONS_VALIDATION.json` | 15 checks — status PASS (TEST) |
| `PERMISSIONS_BEFORE_AFTER.md` | Comparativa antes/después |
| `HEALTHCHECK.json` | Resumen healthcheck TEST PASS |
| `healthcheck.log` | Salida tail del healthcheck TEST |

Script de validación: `scripts/permissions-ux-1-validate.py`

## Cambios realizados

### UX (sin tocar lógica de permisos)

- 10 permisos agrupados en 5 categorías (FINANZAS, OPERACIONES, CONSULTA, ADMINISTRACIÓN DEL ERP, USO INTERNO JUSTECH).
- Pestaña renombrada a **Centro de Permisos**; widget estándar oculto para admins (visible solo en modo técnico).
- 10 tooltips contextuales (`help` en vista + textos en registro UX).
- Estilo diferenciado para permisos internos (badge 🔒 / “Solo soporte autorizado”, SCSS).

### Protección de canal (no cambia ACL/grupos)

- Wizard `hellenia.permissions.internal.wizard` para activar Justech Admin / Justech Platform con Clave Administrativa.
- Reutilización de sesión admin válida; re-prompt si expiró.
- Guard en `res.users.write()` que bloquea asignación directa de grupos internos vía `group_ids` (anti-bypass RPC / edición rápida).
- ACL mínima solo para el wizard transitorio (`ir.model.access.csv`).

### Sin cambios en

- Definición de grupos (`res.groups` / `res.groups.privilege`)
- ACL de modelos de negocio
- Record rules
- Lógica de `hellenia.governance.service` / permisos funcionales
- NCF, DGII, COA, contabilidad, licencias

**Conclusión:** UX + protección de **canal de asignación** de permisos internos. No se alteró la matriz de seguridad subyacente.

## Archivos modificados / nuevos

- `custom/hellenia_governance/models/hellenia_permissions_ux_registry.py` *(nuevo)*
- `custom/hellenia_governance/models/res_users.py`
- `custom/hellenia_governance/models/hellenia_permissions_internal_wizard.py` *(nuevo)*
- `custom/hellenia_governance/views/res_users_permissions_views.xml` *(nuevo)*
- `custom/hellenia_governance/static/src/scss/permissions_ux.scss` *(nuevo)*
- `custom/hellenia_governance/tests/test_permissions_ux.py` *(nuevo)*
- `custom/hellenia_governance/__manifest__.py` — v `19.0.1.2.0`
- `custom/hellenia_governance/models/__init__.py`
- `custom/hellenia_governance/security/ir.model.access.csv`
- `custom/hellenia_governance/tests/__init__.py`
- `scripts/permissions-ux-1-validate.py` *(nuevo)*

## Despliegue

- **TEST:** `-u hellenia_governance` aplicado en VPS (2026-07-07).
- **PROD:** pendiente.

## Estado git

- **Commit:** pendiente (no realizado).
- **Push:** pendiente (no realizado).
- **Merge:** no solicitado.
- HEAD actual en rama: `feature/f31-1-justech-modules` @ `72da371` (BUGFIX-ADMINKEY-2).

## Pendientes sugeridos (fuera de este reporte)

1. Desplegar y validar en PROD (`-u hellenia_governance` + healthcheck + validation script).
2. Commit/push cuando se apruebe.
