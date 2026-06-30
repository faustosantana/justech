# Custom — Desarrollos Justech / Hellenia

**Única carpeta autorizada para código propio.**

## Módulos planificados (esqueleto — sin desarrollo)

| Módulo | Estado | Dependencias base |
|--------|--------|-------------------|
| `hellenia_base` | Esqueleto | `base` |
| `hellenia_inventory` | Esqueleto | `hellenia_base`, `stock` |
| `hellenia_reports` | Esqueleto | `hellenia_base` |
| `hellenia_account` | Esqueleto | `hellenia_base`, `account` |
| `hellenia_pos` | Esqueleto | `hellenia_base`, `point_of_sale` |
| `justech_core` | Esqueleto | `base` |

> **No instalar** estos módulos hasta aprobación explícita. Son placeholders estructurales.

## Estructura de módulo

```
custom/
└── hellenia_<nombre>/
    ├── __init__.py
    ├── __manifest__.py
    ├── models/
    ├── views/
    ├── security/
    │   └── ir.model.access.csv
    └── data/
```

## Convenciones

| Regla | Detalle |
|-------|---------|
| Prefijo | `hellenia_` o `justech_` |
| Herencia | Usar `_inherit` — nunca editar Enterprise/Community |
| Licencia | Declarar en `__manifest__.py` |
| Dependencias | Solo módulos oficiales Odoo salvo aprobación |

## Montaje Docker

```
Host:      /opt/odoo-projects/hellenia/custom/
Container: /mnt/custom (read-only)
```

## Referencia

- [ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- [GIT-STRATEGY.md](../docs/GIT-STRATEGY.md)
