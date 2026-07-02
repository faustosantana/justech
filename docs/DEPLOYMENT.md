# Guía de despliegue — Hellenia

## Pre-requisitos

- DNS: `dev.hellenia.cloud` y `test.hellenia.cloud` → `2.25.69.179`
- Traefik activo (`traefik-traefik-1`)
- Archivos `.env` creados desde `.env.example` (contraseñas distintas DEV vs TEST)

## 1. Configurar secretos

```bash
cp /opt/odoo-projects/hellenia/config/dev/.env.example \
   /opt/odoo-projects/hellenia/config/dev/.env
cp /opt/odoo-projects/hellenia/config/test/.env.example \
   /opt/odoo-projects/hellenia/config/test/.env
chmod 600 /opt/odoo-projects/hellenia/config/*/.env
# Editar passwords con valores seguros y distintos
```

## 2. Levantar DEV

```bash
cd /opt/odoo-projects/hellenia/docker/dev
docker compose --env-file ../../config/dev/.env up -d
```

## 3. Inicializar BD Odoo DEV

```bash
source /opt/odoo-projects/hellenia/config/dev/.env
docker exec hellenia-dev-odoo-1 odoo \
  -d hellenia_dev --db_host=db --db_user=odoo --db_password="$DB_PASSWORD" \
  -i base --stop-after-init --without-demo=all
```

## 4. Levantar TEST

```bash
cd /opt/odoo-projects/hellenia/docker/test
docker compose --env-file ../../config/test/.env up -d
```

## 5. Inicializar BD Odoo TEST

```bash
source /opt/odoo-projects/hellenia/config/test/.env
docker exec hellenia-test-odoo-1 odoo \
  -d hellenia_test --db_host=db --db_user=odoo --db_password="$DB_PASSWORD" \
  -i base --stop-after-init --without-demo=all
```

## 6. Validar Odoo 19

```bash
/opt/odoo-projects/hellenia/scripts/validate-odoo19.sh dev
/opt/odoo-projects/hellenia/scripts/validate-odoo19.sh test
/opt/odoo-projects/hellenia/scripts/healthcheck.sh
```

Documentación: [VERSION-19-ANALYSIS.md](VERSION-19-ANALYSIS.md) | [MIGRATION-19.md](MIGRATION-19.md)

## Flujo Git → ambientes

1. Desarrollar en `feature/*` localmente
2. Merge a `develop` → `deploy-dev.sh develop`
3. Merge a `test` → `deploy-test.sh test`
4. Tras aprobación → backup producción → deploy producción (futuro)
