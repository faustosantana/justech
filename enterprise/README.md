# Enterprise — Código Odoo (independiente de Git Justech)

**Este directorio NO forma parte del repositorio Git Justech.**

## Dos métodos oficiales de obtención

| Método | Script | Documentación |
|--------|--------|---------------|
| **Portal Odoo (recomendado ahora)** | `extract-enterprise-portal.sh` | [E0.6b](../docs/E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md) |
| **GitHub Git** | `clone-enterprise.sh` | [E0.6](../docs/E0.6-GITHUB-ENTERPRISE.md) |
| **Auto (Git → portal)** | `fetch-enterprise.sh` | [ENTERPRISE_ACCESS_OPTIONS](../docs/ENTERPRISE_ACCESS_OPTIONS.md) |

## Portal — procedimiento resumido

1. Descargar **Odoo 19 → Enterprise → Sources** desde [odoo.com/page/download](https://www.odoo.com/page/download)
2. Subir a `downloads/enterprise/`
3. `scripts/extract-enterprise-portal.sh`
4. Montaje Docker: `/mnt/enterprise:ro` (ya configurado)

## Git — cuando el acceso esté habilitado

```bash
/opt/odoo-projects/hellenia/scripts/clone-enterprise.sh
```

## Contenido esperado tras extract/clone

```
enterprise/
├── web_enterprise/
├── l10n_do_edi/          # verificar tras obtener código
├── l10n_do_reports/
└── MANIFEST.txt          # portal: metadatos archivo | git: usar git log
```

## Montaje Docker

```
Host:      /opt/odoo-projects/hellenia/enterprise/
Container: /mnt/enterprise (read-only)
```

## Reglas

- ❌ Nunca commitear a Justech
- ❌ Nunca modificar archivos aquí
- ❌ Nunca copiar módulos a `custom/`
- ✅ Solo addons Enterprise oficiales Odoo

## Licencia

OPL-1.0 — Odoo S.A. Uso permitido con suscripción activa `M260616306091776`.
