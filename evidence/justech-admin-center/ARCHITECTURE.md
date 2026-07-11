# ARQUITECTURA — justech_admin_center

**Fecha:** 2026-07-11  
**Entorno:** erp.justech.do / justech_dev  
**Rama:** feature/fiscal-standard-consolidation  
**Backup preflight:** `/opt/odoo-dev/backups/justech-admin-center-pre-20260711_204746` (restore PASS, login 200)

## 8 puntos (Directiva)

1. **Qué:** Consola central Settings → Administración Justech (`justech_admin_center`).
2. **Por qué:** Un solo lugar funcional para módulos Justech (catálogo, instalar, activar/desactivar, roles, diagnóstico) sin shell/SQL/modo debug.
3. **Riesgos:** Duplicar hub Settings→Justech existente; instalar módulos mal; permisos; CSS invasivo.
4. **Backup:** Dump+filestore+snapshots arriba; restore test descartado.
5. **Rollback:** Restaurar dump; desinstalar solo el módulo nuevo si no hay datos críticos (no desinstalar otros).
6. **Archivos:** `custom/justech_admin_center/**` + registros `justech_admin_center` en manifests Justech; menú bridge con `justech_admin`.
7. **Módulos:** nuevo `justech_admin_center`; soft-links a fiscal_admin, base, ncf, reports, payments, treasury, audit, multicurrency, report_design (sin depends duros).
8. **Tiempo:** implementación + UAT en DEV.

## Decisión de consolidación

| Existente | Acción |
|-----------|--------|
| Settings → **Justech** (`justech_admin`) | Renombrar a **Administración Justech**; acción raíz = consola nueva |
| Settings app Fiscal Justech | Se mantiene como atajo; tile en consola abre Centro Fiscal |
| Centro Fiscal | Dominio fiscal; no se fusiona; se enlaza |
| `justech_register` | Se reutiliza + extensión `justech_admin_center` en manifesto |
| `justech_warranty` | Ausente en repo; discovery runtime si aparece en addons |

## Contrato de registro (sin `if module ==`)

Cada módulo Justech declara en `__manifest__.py`:

```python
"justech_admin_center": {
    "functional_name": "Motor Fiscal NCF",
    "short_description": "...",
    "category": "fiscal",  # fiscal|payments|treasury|audit|reports|platform|ux|integrations
    "icon": "fa-file-invoice",
    "sequence": 20,
    "roles": ["fiscal_user", "fiscal_manager", "fiscal_admin"],
    "capabilities": ["manage_ncf_ranges", "view_dgii_reports"],
    "feature_flag_codes": ["ncf_motor"],
    "open_action_xmlid": "module.action_xxx",  # opcional
    "health_method": "justech.do.ncf.diagnostic.service.run_full_scan",  # opcional dotted
    "supports_activate": True,
    "supports_deactivate": True,
    "critical": True,
}
```

Runtime: `justech.admin.registry.service.discover()` lee manifests de módulos `justech_%` presentes en addons + instalados; upsert a `justech.admin.module`.

## Dependencias del núcleo

```
base, base_setup, web, mail
(+ justech_modules opcional vía try/except / hasattr — NO dependencia Odoo dura)
```

Sin depender de fiscal_admin, hellenia, treasury.

## Modelos

| Modelo | Rol |
|--------|-----|
| `justech.admin.module` | Catálogo (técnico + funcional) |
| `justech.admin.operation` | Cola instalación/activación (lock) |
| `justech.admin.audit.log` | Auditoría inmutable |
| `justech.admin.health.finding` | Diagnóstico |
| `justech.admin.console` | Singleton UI |
| wizards preview | install / activate / deactivate / role |

## Estados

- Técnico: `not_installed` | `installed`
- Funcional: `inactive` | `active` | `attention` | `error`
- Operación: `draft` | `preview` | `running` | `done` | `failed` | `rolled_back`

## Seguridad

- `group_justech_admin_center_user` — ver consola
- `group_justech_admin_center_manager` — instalar/activar/roles
- Reutilizar `base.group_system` para instalaciones
- No eliminar grupos legacy

## UI

Una sola entrada: Configuración → Administración Justech.  
Form/notebook + kanban de módulos + SCSS scoped `.o_justech_admin_center`.  
Sin app en launcher.

## Fases de código

2 Núcleo → 3 Ops → 4 Integraciones registro → 5 Roles/matriz → 6 UAT
