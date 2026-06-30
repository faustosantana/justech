# Custom — Desarrollos Justech / Hellenia

**Única carpeta autorizada para código propio.**

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
| Dependencias | Solo módulos oficiales Odoo salvo aprobación explícita |
| Versionado | Git Justech — rama `hellenia-odoo-infra` o `feature/*` |

## Montaje Docker

```
Host:  /opt/odoo-projects/hellenia/custom/
Container: /mnt/custom (read-only)
```

## Despliegue

Los módulos se sincronizan desde el repo Git Justech:

```bash
rsync -av repository/custom/ /opt/odoo-projects/hellenia/custom/
docker compose restart odoo
```

## Prohibido

- Copiar módulos de `enterprise/` o Community aquí
- Parchear archivos de terceros
- Módulos OCA o externos sin aprobación del cliente

## Referencia

- [ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- [GIT-STRATEGY.md](../docs/GIT-STRATEGY.md)
