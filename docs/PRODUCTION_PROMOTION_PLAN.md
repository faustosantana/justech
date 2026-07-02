# Plan de promoción a producción — Fase 13.7

**Estado actual PROD:** `https://odoo.hellenia.cloud` → **HTTP 404** (Traefik, ver RCA)  
**Estado TEST:** **PASS** (commit `f918576`)  
**Política:** Sin cambios en PROD hasta aprobación explícita + backup

---

## Precondiciones (todas obligatorias)

- [x] RCA documentado (`docs/ROOT_CAUSE_ANALYSIS_404.md`)
- [x] TEST 100% PASS (`evidence/phase13-7-test-functional-validation.json`)
- [x] Mismo commit validado en TEST listo en rama `cursor/phase13-7-test-validation-dd85`
- [ ] **Aprobación explícita** del responsable
- [ ] Backup producción completado

---

## Commit a promover

```
f918576 — Fase 13.7: logo base64, Traefik service label, validación TEST
```

Incluye:

- `docker/production/docker-compose.yml` — label `traefik.http.routers.${COMPOSE_PROJECT_NAME}.service=${COMPOSE_PROJECT_NAME}`
- `docker/test/docker-compose.yml` — paridad Traefik
- `config/test/odoo.conf` — `gevent_port = 8072`
- `custom/hellenia_base/static/img/hellenia_logo.jpg`
- Scripts y documentación Fase 13.7

---

## Secuencia de promoción (solo tras aprobación)

### 1. Backup producción

```bash
ssh deploy@srv.hellenia.cloud
cd /opt/hellenia/justech   # o ruta del clone en servidor
git fetch origin cursor/phase13-7-test-validation-dd85
bash scripts/backup-hellenia-prod.sh
```

Verificar artefacto de backup (dump + filestore) antes de continuar.

### 2. Aplicar commit certificado

```bash
git checkout f918576
# o merge de PR aprobado a rama de despliegue prod
cd docker/production
docker compose pull   # si aplica
docker compose up -d --force-recreate odoo
```

### 3. Post-despliegue Odoo (shell)

```bash
docker compose exec odoo odoo shell -d hellenia_prod --no-http <<'PY'
# Cargar logo (mismo procedimiento que TEST)
import base64
from pathlib import Path
p = Path('/mnt/custom-addons/hellenia_base/static/img/hellenia_logo.jpg')
env['res.company'].browse(1).write({'image_1920': base64.b64encode(p.read_bytes())})
# Limpiar assets huérfanos si aplica
orphans = env['ir.attachment'].search([
    ('store_fname', '!=', False),
    ('type', '=', 'binary'),
])
# Regenerar bundles
env['ir.qweb']._pregenerate_assets_bundles()
env.cr.commit()
PY
```

### 4. Validación post-promoción (checklist)

| # | Verificación | Criterio | Acción si falla |
|---|--------------|----------|-----------------|
| 1 | Traefik logs | Sin error "cannot be linked automatically" | **DETENER** |
| 2 | HTTPS | Certificado válido | **DETENER** |
| 3 | `curl -sI https://odoo.hellenia.cloud/web/login` | HTTP **200** | **DETENER** |
| 4 | Login | Usuario admin accede | **DETENER** |
| 5 | Home | Dashboard carga | **DETENER** |
| 6 | Ventas | Cotización abre, buscar cliente OK | **DETENER** |
| 7 | Compras | RFQ/PO accesible | **DETENER** |
| 8 | Inventario | Productos y quants | **DETENER** |
| 9 | Contabilidad | Asientos / facturas | **DETENER** |
| 10 | PDF factura | Layout `external_layout_hellenia` | **DETENER** |

### 5. Rollback

Si cualquier punto falla:

1. **DETENER** — no aplicar pasos adicionales  
2. Restaurar backup (`scripts/restore-hellenia-prod.sh` si existe)  
3. Revertir compose al commit anterior conocido bueno  
4. Documentar incidente

---

## Fix específico del 404

El cambio crítico es una línea en labels Traefik del servicio `odoo`:

```yaml
- traefik.http.routers.${COMPOSE_PROJECT_NAME}.service=${COMPOSE_PROJECT_NAME}
```

Sin esto, Traefik no enlaza el router `hellenia-prod` cuando coexisten los servicios `hellenia-prod` y `hellenia-prod-ws`.

---

## Decisión actual

| Pregunta | Respuesta |
|----------|-----------|
| ¿TEST certifica el cambio? | **Sí** |
| ¿PROD puede recibir el cambio? | **Sí**, tras aprobación + backup |
| ¿Se modificó PROD en Fase 13.7? | **No** (cumple política) |

**Promoción pendiente de aprobación explícita del usuario.**
