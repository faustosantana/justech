# Custom — Desarrollos Justech / Hellenia

**Única carpeta autorizada para código propio.**

## Módulos (proyectos independientes)

| Módulo | README | Estado |
|--------|--------|--------|
| `justech_core` | [README](justech_core/README.md) | Esqueleto |
| `hellenia_base` | [README](hellenia_base/README.md) | Esqueleto |
| `hellenia_inventory` | [README](hellenia_inventory/README.md) | Esqueleto |
| `hellenia_account` | [README](hellenia_account/README.md) | Esqueleto |
| `hellenia_reports` | [README](hellenia_reports/README.md) | Esqueleto |
| `hellenia_pos` | [README](hellenia_pos/README.md) | Esqueleto |

Cada módulo incluye: `models/`, `views/`, `security/`, `data/`, `static/`, `tests/`, `i18n/`.

**No instalar** hasta aprobación explícita.

## Convenciones

| Regla | Detalle |
|-------|---------|
| Prefijo | `hellenia_` o `justech_` |
| Herencia | `_inherit` — nunca editar Enterprise/Community |
| Estándares | [CODING_STANDARDS.md](../docs/CODING_STANDARDS.md) |
| Guía módulos | [CUSTOM_MODULE_GUIDE.md](../docs/CUSTOM_MODULE_GUIDE.md) |

## Montaje Docker

```
Host:      /opt/odoo-projects/hellenia/custom/
Container: /mnt/custom (read-only)
```

## Despliegue

```bash
/opt/odoo-projects/hellenia/scripts/deploy-dev.sh
/opt/odoo-projects/hellenia/scripts/update-custom-modules.sh dev <modulo>
```
