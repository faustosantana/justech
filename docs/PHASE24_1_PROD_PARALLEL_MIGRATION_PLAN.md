# Fase 24.1 — Plan de migración PROD (reporte paralelo)

**Versión módulo:** `justech_report_design` **v19.0.1.1.6**  
**Entorno origen:** TEST (`hellenia_test` / `test.hellenia.cloud`) — **aprobado visualmente**  
**Entorno destino:** PROD (`hellenia_prod` / `https://odoo.hellenia.cloud`)  
**Modo:** **Reporte paralelo** — opción adicional en Imprimir  
**NO es:** reemplazo del reporte estándar de cotización  

> ⛔ **NO EJECUTAR** hasta autorización final explícita del responsable.  
> Este documento es el plan operativo completo; la ejecución queda bloqueada.

---

## Resumen ejecutivo

| Ítem | Valor |
|------|-------|
| Qué se instala | Solo `custom/justech_report_design/` |
| Qué aparece en UI | **Cotización Hellenia (Diseño)** en menú Imprimir de `sale.order` |
| Qué NO cambia | `sale.action_report_saleorder`, `hellenia_reports`, facturas, DGII, pagos |
| Riesgo datos | Bajo — módulo de reporte + helpers en `sale.order.note` (etiqueta vista) |
| Rollback | Desinstalar módulo (< 15 min) o restaurar backup |
| Commit certificado TEST | `2306747f2f5bea9a0c11bda3a2ceebbab48b1033` |
| Rama | `cursor/phase24-1h-vis001-border-fix-dd85` |

### Aprobaciones recibidas

- [x] Diseño cotización v19.0.1.1.6 aprobado visualmente (VIS-001 cerrado)
- [x] Flujo vertical 24.1H (CONDICIONES / FIRMAS separados)
- [ ] **Autorización escrita para ejecutar en PROD** — pendiente

---

## Alcance y límites

### Dentro de alcance

- Instalar `justech_report_design` en PROD
- Validar PDF paralelo en cotización real
- Confirmar que **Cotización en PDF** (estándar) sigue disponible y funcional
- Documentar evidencia post-instalación

### Fuera de alcance (explícitamente NO hacer)

- Reemplazar `sale.action_report_saleorder` como default
- Modificar `hellenia_reports` ni herencias xpath de cotización estándar
- Portal PDF del reporte Justech
- Promoción de facturas, compras, inventario (Fase 24.2)
- Cambios de diseño adicionales

---

## 1. Backup previo (obligatorio)

### 1.1 Cuándo

Inmediatamente **antes** de copiar el módulo o ejecutar `-i justech_report_design` en PROD.

### 1.2 Comando estándar (VPS)

```bash
# En el VPS de producción
cd /opt/odoo-projects/hellenia
./scripts/backup-hellenia-prod.sh
```

### 1.3 Qué incluye el backup

| Artefacto | Archivo |
|-----------|---------|
| PostgreSQL (pg_dumpall) | `postgres_all.sql.gz` |
| Filestore Odoo | `filestore.tar.gz` |
| Módulos custom | `custom.tar.gz` |
| Docker compose PROD | `docker-compose.yml` |
| Config Odoo | `odoo.conf` |
| Variables entorno | `.env` |
| Manifiesto | `MANIFEST.txt` |

**Ruta típica:** `/opt/odoo-projects/hellenia/backups/hellenia-prod/YYYY-MM-DD_HHMM/`

### 1.4 Verificación del backup (checklist)

- [ ] Script termina sin error
- [ ] Existe `postgres_all.sql.gz` (> 1 MB)
- [ ] Existe `filestore.tar.gz`
- [ ] Existe `custom.tar.gz`
- [ ] Anotar ruta del backup: `________________________`

### 1.5 Restauración completa (solo emergencia)

```bash
/opt/odoo-projects/hellenia/scripts/restore-hellenia-prod.sh \
  /opt/odoo-projects/hellenia/backups/hellenia-prod/<TIMESTAMP>
```

Usar solo si desinstalar el módulo no es suficiente o hay corrupción de datos.

---

## 2. Instalación del módulo

### 2.1 Pre-requisitos técnicos

- [ ] Commit/rama certificada en VPS: `2306747` o merge a rama de release acordada
- [ ] Backup PROD verificado (sección 1)
- [ ] Autorización escrita del responsable
- [ ] Ventana acordada (baja criticidad — sin downtime prolongado)

### 2.2 Sincronizar código en VPS

**Opción A — Desde Git (recomendada)**

```bash
cd /opt/odoo-projects/hellenia
# Actualizar repositorio al commit certificado
cd repository   # o ruta git del proyecto
git fetch origin
git checkout 2306747f2f5bea9a0c11bda3a2ceebbab48b1033
# Sincronizar solo el módulo a custom/
rsync -a --delete repository/custom/justech_report_design/ custom/justech_report_design/
```

**Opción B — Desde artefacto ZIP**

```bash
# Subir packages/justech_report_design-v19.0.1.1.6.zip al VPS
cd /opt/odoo-projects/hellenia/custom
rm -rf justech_report_design
unzip -q /tmp/justech_report_design-v19.0.1.1.6.zip -d .
```

**Verificar versión:**

```bash
grep '"version"' custom/justech_report_design/__manifest__.py
# Debe mostrar: "version": "19.0.1.1.6",
```

### 2.3 Qué NO copiar a PROD

- `evidence/`
- `scripts/phase24-1-*-test.py`
- `packages/phase24-1-hellenia-quotation-review/`
- Configuración TEST (`config/test/`)

### 2.4 Instalar módulo (primera vez en PROD)

```bash
cd /opt/odoo-projects/hellenia
source config/production/.env

# Detener Odoo (opcional pero recomendado para upgrade limpio)
docker stop hellenia-prod-odoo-1

docker run --rm --network hellenia-prod_default \
  -v hellenia-prod_odoo-data:/var/lib/odoo \
  -v /opt/odoo-projects/hellenia/enterprise:/mnt/enterprise:ro \
  -v /opt/odoo-projects/hellenia/custom:/mnt/custom:ro \
  -v /opt/odoo-projects/hellenia/config/production/odoo.conf:/etc/odoo/odoo.conf:ro \
  -e HOST=db -e USER="${DB_USER}" -e PASSWORD="${DB_PASSWORD}" \
  odoo:19.0-20260619 \
  odoo -d hellenia_prod \
  -i justech_report_design \
  --stop-after-init --no-http \
  --db_host=db --db_user="${DB_USER}" --db_password="${DB_PASSWORD}"

docker start hellenia-prod-odoo-1
```

**Si el módulo ya existiera en PROD (actualización):** cambiar `-i` por `-u justech_report_design`.

### 2.5 Verificación técnica inmediata

```bash
docker exec hellenia-prod-odoo-1 odoo shell -d hellenia_prod --no-http <<'PY'
mod = env['ir.module.module'].search([('name','=','justech_report_design')], limit=1)
print('state', mod.state, 'version', mod.latest_version)
action = env.ref('justech_report_design.action_report_hellenia_quotation', raise_if_not_found=False)
std = env.ref('sale.action_report_saleorder', raise_if_not_found=False)
print('jt_action', action.name if action else None)
print('std_action', std.report_name if std else None)
PY
```

**Resultado esperado:**

| Campo | Valor esperado |
|-------|----------------|
| `state` | `installed` |
| `version` | `19.0.1.1.6` |
| `jt_action` | `Cotización Hellenia (Diseño)` |
| `std_action` | `sale.report_saleorder` (sin cambios) |

---

## 3. Validación en cotización real (PROD)

### 3.1 Seleccionar cotización de prueba

Usar una cotización **real** en borrador o enviada, con:

- [ ] Al menos 1 línea de producto
- [ ] Cliente con datos completos (nombre, teléfono si aplica)
- [ ] Campo **Condiciones (PDF Cotización)** (`note`) con texto representativo
- [ ] Preferible: una con 1 producto y otra con 5+ líneas (misma nota para comparar)

**No usar** referencias de TEST (`P23-3-QUOTE-*`).

### 3.2 Generar PDF paralelo

1. Abrir cotización en PROD UI
2. **Imprimir** → seleccionar **Cotización Hellenia (Diseño)**
3. Descargar / visualizar PDF

### 3.3 Criterios de aceptación visual

| # | Criterio | OK / FAIL |
|---|----------|-----------|
| 1 | Logo Hellenia visible, proporción correcta | |
| 2 | Banda verde COTIZACIÓN + número | |
| 3 | Tabla productos legible | |
| 4 | Totales compactos a la derecha | |
| 5 | CONDICIONES inmediatamente después de totales | |
| 6 | **Sin rectángulo/borde** alrededor de condiciones o firmas (VIS-001) | |
| 7 | Firmas cerca del footer | |
| 8 | Footer verde con teléfono, email, paginación | |
| 9 | Con descuento en línea: columna DESC. y desglose en totales | |
| 10 | Idioma/moneda del cliente correctos | |

### 3.4 Evidencia a guardar

```
evidence/phase24-1-prod-parallel/
├── prod_quotation_real_1p.pdf
├── prod_quotation_real_5p.pdf
├── prod_quotation_standard.pdf      # reporte estándar misma cotización
├── validation_notes.md
└── MANIFEST.txt
```

---

## 4. Verificar reporte estándar sigue disponible

### 4.1 En UI

- [ ] Menú **Imprimir** muestra **ambas** opciones:
  - **Cotización en PDF** (o nombre estándar Odoo / hellenia_reports)
  - **Cotización Hellenia (Diseño)** ← nuevo
- [ ] Imprimir con **Cotización en PDF** genera el diseño **anterior** (sin regresión)

### 4.2 Verificación técnica

```bash
docker exec hellenia-prod-odoo-1 odoo shell -d hellenia_prod --no-http <<'PY'
so = env['sale.order'].search([('state','in',('draft','sent'))], limit=1)
if not so:
    print('SKIP: sin cotización')
else:
    std = env.ref('sale.action_report_saleorder')
    pdf, _ = env['ir.actions.report']._render_qweb_pdf(std.report_name, so.ids)
    print('standard_pdf_ok', pdf[:4] == b'%PDF', 'size', len(pdf))
    jt = env.ref('justech_report_design.action_report_hellenia_quotation')
    pdf2, _ = env['ir.actions.report']._render_qweb_pdf(jt.report_name, so.ids)
    print('jt_pdf_ok', pdf2[:4] == b'%PDF', 'size', len(pdf2))
    print('std_report_name', std.report_name)
    print('jt_report_name', jt.report_name)
PY
```

### 4.3 Sin herencia sobre estándar

```bash
docker exec hellenia-prod-odoo-1 odoo shell -d hellenia_prod --no-http <<'PY'
for key in ('sale.report_saleorder','sale.report_saleorder_document','sale.report_saleorder_raw'):
    v = env['ir.ui.view'].search([('key','=',key)], limit=1)
    children = env['ir.ui.view'].search([('inherit_id','=',v.id),('key','like','justech_report_design.%')])
    print(key, 'jt_inherits', len(children))
PY
```

**Esperado:** `jt_inherits 0` en los tres.

### 4.4 Regresión rápida otros dominios (smoke)

- [ ] Imprimir **una factura** posted — PDF OK
- [ ] Imprimir **una orden de compra** — PDF OK
- [ ] Sin errores nuevos en logs (`RPC_ERROR`, `QWebException`) tras 5 min

---

## 5. Rollback documentado

### 5.1 Rollback rápido — desinstalar módulo (recomendado primero)

**Impacto:** desaparece menú **Cotización Hellenia (Diseño)**. Reporte estándar intacto.  
**Datos:** no debería afectar cotizaciones; el campo `note` sigue existiendo en `sale.order`.

```bash
cd /opt/odoo-projects/hellenia
source config/production/.env

docker exec hellenia-prod-odoo-1 odoo shell -d hellenia_prod --no-http <<'PY'
env['ir.module.module'].search([('name','=','justech_report_design')]).button_immediate_uninstall()
env.cr.commit()
PY

docker restart hellenia-prod-odoo-1
```

**Verificar post-rollback:**

- [ ] Módulo no aparece en Aplicaciones como Instalado
- [ ] Solo reporte estándar en Imprimir
- [ ] PDF estándar genera correctamente

### 5.2 Rollback código — eliminar módulo del filesystem

```bash
rm -rf /opt/odoo-projects/hellenia/custom/justech_report_design
docker restart hellenia-prod-odoo-1
```

Ejecutar solo **después** de desinstalar desde Odoo (5.1).

### 5.3 Rollback completo — restaurar backup

Usar si hay corrupción o comportamiento inesperado en datos:

```bash
/opt/odoo-projects/hellenia/scripts/restore-hellenia-prod.sh \
  /opt/odoo-projects/hellenia/backups/hellenia-prod/<TIMESTAMP_PRE_INSTALACION>
```

**Tiempo estimado:** 10–30 min según tamaño de BD.

### 5.4 Matriz de decisión rollback

| Síntoma | Acción |
|---------|--------|
| PDF Justech con error QWeb | Desinstalar módulo (5.1) |
| Estilos no cargan | Reinicio Odoo; si persiste, `-u justech_report_design` o desinstalar |
| Reporte estándar roto | **Restaurar backup** — investigar antes de reintentar |
| Usuarios confundidos | Desinstalar o capacitar; no tocar estándar |
| Error en facturas/DGII | Desinstalar + verificar logs; restaurar backup si persiste |

---

## 6. Checklist post-instalación

Completar en las **24–48 h** siguientes a la instalación.

### 6.1 Funcional

- [ ] `justech_report_design` **Instalado** v`19.0.1.1.6`
- [ ] **Cotización Hellenia (Diseño)** visible en Imprimir
- [ ] **Cotización en PDF** estándar sigue visible y funcional
- [ ] PDF real 1 producto — PASS visual
- [ ] PDF real 5+ productos — PASS visual y paginación
- [ ] PDF con descuento en línea — columna y totales OK
- [ ] Campo **Condiciones (PDF Cotización)** editable en formulario cotización
- [ ] Sin rectángulo VIS-001 en PDFs PROD

### 6.2 No regresión

- [ ] Factura PDF — OK
- [ ] Pago / recibo — OK (si aplica)
- [ ] Compra / RFQ — OK
- [ ] Albarán — OK
- [ ] Reportes DGII — OK (smoke UI)
- [ ] Logs PROD sin `QWebException` nuevos relacionados a `justech_report_design`

### 6.3 Operación

- [ ] Backup pre-instalación documentado con timestamp
- [ ] Evidencia PDF guardada en `evidence/phase24-1-prod-parallel/`
- [ ] Usuarios informados: cuándo usar **Diseño** vs **estándar**
- [ ] Rollback probado en documentación (no ejecutar salvo incidente)
- [ ] Monitoreo 48h — sin tickets críticos de impresión

### 6.4 Registro de ejecución (completar al promover)

| Campo | Valor |
|-------|-------|
| Fecha ejecución | _pendiente_ |
| Ejecutado por | _pendiente_ |
| Autorizado por | _pendiente_ |
| Backup usado | _pendiente_ |
| Commit desplegado | `2306747` |
| Versión módulo | `19.0.1.1.6` |
| Cotización prueba 1 | _pendiente_ |
| Cotización prueba 2 | _pendiente_ |
| Rollback necesario | _pendiente_ |
| Resultado final | _pendiente_ |

---

## Comandos de referencia rápida

```bash
# 1. Backup
./scripts/backup-hellenia-prod.sh

# 2. Instalar (primera vez)
docker run --rm --network hellenia-prod_default ... \
  odoo -d hellenia_prod -i justech_report_design --stop-after-init --no-http

# 3. Reiniciar
docker start hellenia-prod-odoo-1

# 4. Rollback
docker exec hellenia-prod-odoo-1 odoo shell -d hellenia_prod --no-http -c \
  "env['ir.module.module'].search([('name','=','justech_report_design')]).button_immediate_uninstall()"
```

---

## Próxima fase (NO incluida en este plan)

Cuando se autorice **formato oficial** (reemplazo del estándar):

1. Decisión de negocio documentada
2. Fase 24.1I — cambiar binding o `sale.action_report_saleorder`
3. Evaluar desactivar herencias cotización en `hellenia_reports`
4. Nueva ventana de mantenimiento + backup + rollback específico

---

## Referencias

| Recurso | Ruta |
|---------|------|
| Auditoría TEST | `docs/PHASE24_1G_QUOTATION_AUDIT.md` |
| Diagnóstico flujo vertical | `docs/PHASE24_1H_VERTICAL_FLOW_DIAGNOSIS.md` |
| ZIP revisión aprobado | `packages/phase24-1-hellenia-quotation-review.zip` |
| Módulo v19.0.1.1.6 | `packages/justech_report_design-v19.0.1.1.6.zip` |
| Checklist legado | `packages/phase24-1-hellenia-quotation-review/PROD_PROMOTION_CHECKLIST.md` |
| Promoción previa referencia | `docs/PHASE23_2_PROD_VISUAL_DEPLOYMENT.md` |

---

**Estado:** 📋 **PLAN LISTO** — ejecución bloqueada hasta autorización final.

*Última actualización: 2026-07-02 — Fase 24.1 PROD paralelo*
