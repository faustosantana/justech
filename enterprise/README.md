# Enterprise — Repositorio Odoo (independiente)

**Este directorio NO forma parte del repositorio Git Justech.**

## Clonación (Fase E1)

```bash
/opt/odoo-projects/hellenia/scripts/clone-enterprise.sh
```

Clona `https://github.com/odoo/enterprise.git` rama `19.0` en este directorio.

## Requisitos previos

1. Suscripción Enterprise activa (`M260616306091776`)
2. Usuario GitHub vinculado en [odoo.com/my/subscriptions](https://www.odoo.com/my/subscriptions)
3. Credenciales en `config/credentials/github.env` (chmod 600)

Ver [docs/E0.6-GITHUB-ENTERPRISE.md](../docs/E0.6-GITHUB-ENTERPRISE.md)

## Actualización

```bash
cd /opt/odoo-projects/hellenia/enterprise
git pull origin 19.0
```

## Reglas

- ❌ Nunca commitear a Justech
- ❌ Nunca modificar archivos aquí
- ❌ Nunca copiar módulos a `custom/`
- ✅ Montado read-only en Docker: `/mnt/enterprise`

## Licencia

OPL-1.0 — Odoo S.A. Uso permitido con suscripción activa.
