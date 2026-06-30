# Guía de Despliegue — Producción Odoo 19

**URL:** https://odoo.hellenia.cloud  
**Estado:** Plantilla certificada — **NO DESPLEGAR** sin checklist Go-Live

---

## 1. Prerrequisitos

- [ ] Aprobación Go-Live firmada
- [ ] Backup triple Fase 10 verificado
- [ ] Rama `feature/justech-l10n-do-mvp` mergeada o tag release
- [ ] Enterprise addons en `/opt/odoo-projects/hellenia/enterprise/addons`
- [ ] Custom addons en `/opt/odoo-projects/hellenia/custom`

---

## 2. Archivos de referencia

| Archivo | Propósito |
|---------|-----------|
| `docker/production/docker-compose.yml` | Stack `hellenia-prod` |
| `config/production/.env.example` | Variables (copiar a `.env`) |
| `config/production/odoo.conf.example` | Odoo config producción |

---

## 3. Procedimiento (NO ejecutar en Fase 10)

### 3.1 Preparar configuración

```bash
cd /opt/odoo-projects/hellenia
cp config/production/.env.example config/production/.env
cp config/production/odoo.conf.example config/production/odoo.conf
# Editar contraseñas — NO commitear
```

### 3.2 Crear base de datos (primera vez)

```bash
cd docker/production
docker compose --env-file ../../config/production/.env up -d db
# Esperar healthy
docker compose --env-file ../../config/production/.env run --rm odoo \
  odoo -d hellenia_prod -i base --stop-after-init --without-demo=all
```

### 3.3 Instalar módulos MVP

Usar scripts existentes adaptados a `prod`:

```bash
./scripts/install-enterprise-dev.sh   # patrón — crear install-prod equivalente al Go-Live
./scripts/install-phase6-mvp-module.sh prod
./scripts/apply-phase8-parameterization.sh prod
```

### 3.4 Levantar stack completo (sin DNS público inicial)

```bash
cd docker/production
docker compose --env-file ../../config/production/.env up -d
```

### 3.5 Traefik

Labels en `docker-compose.yml`:

```yaml
traefik.http.routers.hellenia-prod.rule=Host(`odoo.hellenia.cloud`)
traefik.http.routers.hellenia-prod.tls.certresolver=letsencrypt
```

**Validar internamente** antes de comunicar URL a usuarios.

### 3.6 Parámetros Odoo

```text
web.base.url = https://odoo.hellenia.cloud
proxy_mode = True
dbfilter = ^hellenia_prod$
```

### 3.7 Licencia Enterprise

Registrar código `M260616306091776` **solo** en `hellenia_prod`. Desvincular BD legacy antes si aplica.

---

## 4. Workers y recursos (VPS actual)

| Recurso | Valor auditado | Recomendación |
|---------|----------------|---------------|
| RAM | 7.8 GB | `workers = 2` inicial (conservador) |
| CPU | 2 vCPU | Monitorear carga |
| Disco | 79 GB libres | OK |
| Swap | 0 | Considerar 2GB swap pre-Go-Live |

Plantilla `odoo.conf.example` sugiere `workers = 4` — **ajustar a 2** en hardware actual.

---

## 5. Verificación post-despliegue (smoke)

| # | Prueba |
|---|--------|
| 1 | Login `it@justech.do` |
| 2 | Empresa Hellenia configurada |
| 3 | Módulos Justech instalados |
| 4 | Factura prueba con NCF (rango real) |
| 5 | HTTPS LE válido |
| 6 | Backup automático configurado |

---

## 6. Estado Fase 10

**PASS CON OBSERVACIONES** — plantilla lista, servicio no iniciado.

**Bloqueantes:** despliegue real, certificado LE, licencia PROD.
