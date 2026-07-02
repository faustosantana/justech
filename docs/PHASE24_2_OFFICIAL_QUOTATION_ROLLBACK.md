# Fase 24.2 — Rollback cotización oficial (< 2 minutos)

Revertir el reporte principal de cotización al estándar **sin tocar datos** de cotizaciones, facturas ni DGII.

## Opción A — Shell Odoo (recomendada, ~60 s)

```bash
cd /opt/odoo-projects/hellenia
source config/<test|production>/.env
CONTAINER=hellenia-<test|prod>-odoo-1

docker exec "$CONTAINER" odoo shell -d <hellenia_test|hellenia_prod> --no-http <<'PY'
action = env.ref('sale.action_report_saleorder')
action.write({
    'report_name': 'sale.report_saleorder',
    'report_file': 'sale.report_saleorder',
    'paperformat_id': env.ref('hellenia_reports.paperformat_hellenia_letter').id,
})
# Re-vincular acción paralela al menú si se desea convivencia
jt = env.ref('justech_report_design.action_report_hellenia_quotation')
jt.write({
    'binding_model_id': env.ref('sale.model_sale_order').id,
    'binding_type': 'report',
})
env.cr.commit()
print('rollback_ok', action.report_name)
PY

docker restart "$CONTAINER"
```

**Verificar (< 30 s):**

1. Imprimir cotización → menú **Cotización en PDF (Respaldo)** ya no es necesario; el principal vuelve al diseño `hellenia_reports` / estándar.
2. PDF genera sin error.
3. Campo `note` en cotizaciones **no se modifica** (datos intactos).

## Opción B — Desinstalar solo el XML oficial (upgrade inverso)

Si se despliega una revisión de módulo con `report_official_data.xml` retirado:

```bash
docker stop hellenia-<env>-odoo-1
docker run --rm --network hellenia-<env>_default \
  -v hellenia-<env>_odoo-data:/var/lib/odoo \
  -v /opt/odoo-projects/hellenia/enterprise:/mnt/enterprise:ro \
  -v /opt/odoo-projects/hellenia/custom:/mnt/custom:ro \
  -v /opt/odoo-projects/hellenia/config/<env>/odoo.conf:/etc/odoo/odoo.conf:ro \
  -e HOST=db -e USER="$DB_USER" -e PASSWORD="$DB_PASSWORD" \
  odoo:19.0-20260619 \
  odoo -d <db> -u justech_report_design --stop-after-init --no-http \
  --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD"
docker start hellenia-<env>-odoo-1
```

(Requiere commit que revierta `data/report_official_data.xml`.)

## Opción C — Emergencia datos (no suele hacer falta)

Solo si hay corrupción de datos tras un incidente:

```bash
./scripts/restore-hellenia-prod.sh backups/hellenia-prod/<TIMESTAMP>
```

## Qué NO hace el rollback

| Elemento | Efecto rollback |
|----------|-----------------|
| `sale.order.note` por cotización | **Intacto** |
| `res.company.hellenia_quotation_terms` | **Intacto** |
| Facturas / compras / inventario / DGII | **Sin cambios** |
| `hellenia_reports` | **Sigue instalado** |
| `sale.report_saleorder` (template) | **No se elimina** |

## Matriz rápida

| Síntoma | Acción |
|---------|--------|
| PDF oficial con error QWeb | Opción A |
| Usuarios prefieren diseño anterior | Opción A |
| Necesidad de volver a modo paralelo 24.1 | Opción A + re-bind `action_report_hellenia_quotation` |
| Corrupción BD | Opción C |

**Tiempo objetivo:** < 2 minutos con Opción A + restart.
