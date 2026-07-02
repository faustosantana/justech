# FASE 24.1G — Auditoría final antes de promover cotización a formato oficial

**Fecha:** 2026-07-02  
**Entorno auditado:** TEST (`hellenia_test` / `test.hellenia.cloud`)  
**Módulo:** `justech_report_design` v`19.0.1.1.3`  
**Rama:** `cursor/phase24-1g-quotation-audit-dd85`  
**PROD:** ⛔ **NO tocado** — **NO promovido**

---

## Veredicto ejecutivo

| Pregunta | Respuesta |
|----------|-----------|
| ¿Listo para migrarse como **formato oficial** de cotización? | **NO** |
| ¿Listo para promoción a PROD como reporte **paralelo**? | **Casi** — pendiente aprobación visual y resolución VIS-001 |
| ¿Rompe reportes estándar de venta? | **NO** |
| ¿Funciona técnicamente en TEST? | **SÍ** — todos los checks automáticos PASS |

**Bloqueantes para formato oficial:**

1. **VIS-001** — rectángulo/borde gris visible alrededor de CONDICIONES + firmas (`jt-hq-lower`).
2. **Aprobación visual** del responsable (Fausto) pendiente sobre paquete de revisión.
3. **Decisión de negocio** explícita para reemplazar el reporte estándar (no solo instalar en paralelo).

---

## Resumen PASS/FAIL por punto de auditoría

| # | Área | Resultado | Evidencia |
|---|------|-----------|-----------|
| 1 | Reportes estándar no rotos | **PASS** | `audit.json` → `1_standard_reports` |
| 2 | Reporte Justech paralelo (no reemplaza) | **PASS** | `audit.json` → `2_parallel_report` |
| 3 | Dependencias (assets, paperformat, QWeb, action, binding) | **PASS** | `audit.json` → `3_dependencies` |
| 4 | Campos usados (note, discount, impuestos, sin mobile) | **PASS** | `audit.json` → `4_fields` |
| 5 | Escenarios funcionales (1/5/25/discount/note/confirmada) | **PASS** | `audit.json` → `scenarios` |
| 6 | Validación PDF (backend, totales, logo, footer, etc.) | **PASS** | `validation.json` 24.1F + escenarios 24.1G |
| 7 | Aislamiento (facturas, pagos, compras, inventario, DGII, portal) | **PASS** | `audit.json` → `7_isolation` |
| 8 | Issue visual VIS-001 | **PENDIENTE** | Bloqueante para oficial |
| 9 | Aprobación visual responsable | **PENDIENTE** | `docs/PHASE24_STATUS.md` |
| 10 | Portal PDF público | **INFO** (no bloqueante backend) | URL devuelve HTML ~7 KB, no PDF |

**Script automático:** `scripts/phase24-1g-quotation-audit.py`  
**Evidencia JSON:** `evidence/phase24-1g-audit/audit.json`  
**Última ejecución TEST:** `2026-07-02T03:38 UTC` — `ready_for_official: false` (solo por `visual_pending`)

---

## 1. Reportes estándar no rotos

| Check | Resultado | Detalle |
|-------|-----------|---------|
| `sale.report_saleorder` existe | PASS | Vista QWeb intacta |
| Sin herencia `justech_report_design` en saleorder | PASS | 0 vistas hijas |
| `sale.report_saleorder_document` existe | PASS | |
| Sin herencia JT en document | PASS | |
| `sale.report_saleorder_raw` existe | PASS | |
| Sin herencia JT en raw | PASS | |
| `sale.action_report_saleorder` apunta a estándar | PASS | `report_name = sale.report_saleorder` |
| PDF estándar renderiza | PASS | ~73 KB |

**Nota:** `hellenia_reports` **sí** hereda `sale.report_saleorder_document` y `sale.report_saleorder_raw` con diseño Hellenia legacy (xpath). Eso es independiente de `justech_report_design` y sigue activo en paralelo.

---

## 2. Reporte Justech paralelo

| Check | Resultado | Detalle |
|-------|-----------|---------|
| Action `action_report_hellenia_quotation` | PASS | Nombre menú: **Cotización Hellenia (Diseño)** |
| `report_name` propio | PASS | `justech_report_design.report_hellenia_quotation_document` |
| No usa `sale.report_saleorder` | PASS | |
| Binding `sale.order` tipo `report` | PASS | Aparece en Imprimir junto al estándar |
| Coexistencia múltiples reportes | PASS | 4 acciones PDF en `sale.order`: Diseño, Cotización en PDF, Cotización/orden, Factura PROFORMA |

El módulo **no reemplaza** el reporte por defecto. Usuario debe elegir explícitamente **Cotización Hellenia (Diseño)**.

---

## 3. Dependencias técnicas

| Componente | Archivo / registro | Estado |
|------------|-------------------|--------|
| Dependencia módulo | `depends: ["sale"]` | PASS |
| Assets PDF | `web.report_assets_common` → `hellenia_quotation.scss` | PASS — clases `jt-hq-band`, `jt-hq-logo` en HTML y bundle |
| Paperformat | `paperformat_hellenia_quotation` — Letter, DPI 90, márgenes compactos | PASS |
| QWeb body | `justech_report_design.hellenia_quotation_body` | PASS |
| QWeb document | `justech_report_design.report_hellenia_quotation_document` | PASS |
| Action report | `data/report_action_data.xml` | PASS |
| Binding sale.order | `binding_model_id` + `binding_type=report` | PASS |
| Layout | `web.html_container` — **sin** `web.external_layout` | PASS |

---

## 4. Campos y datos usados

| Campo / dato | Uso | Validación |
|--------------|-----|------------|
| `sale.order.note` | Condiciones PDF vía `get_jt_quotation_terms_display()` | PASS — fallback a `_JT_DEFAULT_TERMS` si vacío |
| `sale.order.line.discount` | Columna DESC. condicional + totales desglosados | PASS |
| `amount_untaxed`, `amount_tax`, `amount_total` | Totales oficiales Odoo | PASS — `total_matches` en escenario descuento |
| `partner_id.phone` | Contacto cliente | PASS |
| `partner.mobile` | **No usado** | PASS — ausente en template y HTML |
| `company.logo` | Header | PASS — `image_data_uri(company.logo)` |
| `currency_id` | Formato moneda | PASS — USD en escenario descuento |

**Helpers Python** (`models/sale_order.py`): `format_jt_monetary`, `format_jt_discount_percent`, `get_jt_quotation_gross_subtotal`, `get_jt_quotation_discount_total`, `get_jt_quotation_signature_push_px`, etc.

---

## 5. Escenarios funcionales

| Escenario | Orden TEST | Ref | Resultado |
|-----------|------------|-----|-----------|
| 1 producto sin descuento | S00134 | P23-3-QUOTE-1P | **PASS** |
| 5 productos sin descuento | S00135 | P23-3-QUOTE-5P | **PASS** |
| 25 productos sin descuento | S00138 | P23-3-QUOTE-25P | **PASS** |
| 5 productos con descuento 10% | S00139 | P24-1E-QUOTE-5P-DISC | **PASS** — columna DESC., Subtotal bruto → Descuento → Subtotal → ITBIS → TOTAL |
| Sin note (términos por defecto) | S00140 | P24-1G-AUDIT-NO-NOTE | **PASS** |
| Note editado | S00135 | (temporal auditoría) | **PASS** |
| Cotización confirmada (orden venta) | S00128 | state=sale | **PASS** |

---

## 6. Validación PDF

| Aspecto | Resultado | Notas |
|---------|-----------|-------|
| Backend Imprimir → PDF | PASS | `_render_qweb_pdf` válido en todos los escenarios |
| Descarga PDF | PASS | Archivos en `evidence/phase24-1g-audit/audit_*.pdf` |
| Idioma cliente | PASS | Contexto `lang=partner.lang` renderiza sin error |
| Moneda | PASS | Símbolo USD presente |
| Paginación | PASS | Marcadores `class="page"` / `class="topage"` |
| Footer | PASS | `jt-hq-footer-pdf` presente |
| Logo | PASS | `jt-hq-logo` + `company.logo` |
| Totales compactos derecha | PASS | `jt-hq-totals-wrap` width 280px |
| Descuentos | PASS | Columna y desglose en totales cuando aplica |
| Sin `external_layout` legacy | PASS | |

**Portal (informativo):** `/report/pdf/justech_report_design...?access_token=...` devuelve HTML (~7 KB), no PDF. Fuera de alcance 24.1 backend; no bloquea promoción paralela.

---

## 7. Aislamiento — no afecta otros dominios

| Dominio | Reporte JT | PDF estándar | Resultado |
|---------|------------|--------------|-----------|
| Facturas (`account.move`) | No | PASS (factura posted) | PASS |
| Pagos (`account.payment`) | No | N/A | PASS |
| Compras (`purchase.order`) | No | PASS (~24 KB) | PASS |
| Inventario (`stock.picking`) | No | PASS (~15 KB) | PASS |
| DGII / fiscal | Sin herencias JT en account | — | PASS |
| Contabilidad | Sin vistas JT en account.move | — | PASS |
| Portal | Sin cambio de rutas estándar | INFO | No bloqueante |

`justech_report_design` solo añade: report action, paperformat, SCSS, helpers en `sale.order`, etiqueta vista `note`.

---

## 8. Riesgos identificados

| ID | Severidad | Riesgo | Mitigación |
|----|-----------|--------|------------|
| **VIS-001** | Alta (visual) | Borde/contorno gris en zona `jt-hq-lower` (condiciones + firmas) visible en PDF 1 producto | Corregir SCSS/template antes de oficial; no promover sin OK visual |
| **R-002** | Media | Coexistencia `hellenia_reports` + `justech_report_design` — tres diseños de cotización posibles | Al hacer oficial, desactivar o alinear herencias legacy en `hellenia_reports` |
| **R-003** | Media | Usuarios pueden imprimir reporte equivocado (estándar vs Diseño) | Capacitación + eventual reemplazo de action por defecto |
| **R-004** | Baja | Portal no sirve PDF del reporte JT | Fase futura; no bloquea backend |
| **R-005** | Baja | `note` compartido entre UI cotización y PDF — edición afecta impresión | Documentado en vista: "Condiciones (PDF Cotización)" |
| **R-006** | Baja | wkhtmltopdf interpreta tablas/bordes distinto al navegador | Validar siempre con PDF real, no solo HTML |

---

## 9. Archivos del módulo (alcance del cambio)

```
custom/justech_report_design/
├── __manifest__.py                    # v19.0.1.1.3
├── __init__.py
├── models/
│   ├── __init__.py
│   └── sale_order.py                  # helpers cotización
├── report/quotation/
│   └── hellenia_quotation_template.xml
├── views/sale_order_views.xml         # note → "Condiciones (PDF Cotización)"
├── data/
│   ├── paperformat_data.xml
│   └── report_action_data.xml
└── static/src/scss/
    └── hellenia_quotation.scss
```

**Scripts de auditoría (no desplegar a PROD):**

- `scripts/phase24-1g-quotation-audit.py`
- `scripts/run-phase24-1g-audit.sh`
- `evidence/phase24-1g-audit/audit.json`

---

## 10. Issue visual pendiente — VIS-001

**Descripción:** En cotización de 1 producto persiste un rectángulo o contorno gris claro que envuelve la zona inferior (tabla `jt-hq-lower`: CONDICIONES + spacer + firmas).

**Estado:** PENDIENTE — **bloqueante para aprobación como formato oficial**.

**Ubicación técnica:**

- Template: `report/quotation/hellenia_quotation_template.xml` — `<table class="jt-hq-lower">`
- SCSS: `static/src/scss/hellenia_quotation.scss` — reglas `.jt-hq-lower`, `.jt-hq-cond`, `.jt-hq-sigs`

**Evidencia visual:** `evidence/phase24-1-report-design/quotation_1_product.png` (paquete revisión ZIP).

**Acción requerida antes de oficial:** Eliminar contorno visible en wkhtmltopdf sin reintroducir cajas en firmas. **No modificar sin autorización explícita** (instrucción fase 24.1G).

---

## 11. Rollback plan

### En TEST (actual)

```bash
# Desde UI: Aplicaciones → Justech Report Design → Desinstalar
# O odoo shell:
env['ir.module.module'].search([('name','=','justech_report_design')]).button_immediate_uninstall()
```

Efecto: desaparece menú **Cotización Hellenia (Diseño)**; reportes estándar y `hellenia_reports` siguen igual.

### En PROD (cuando se promueva — NO ejecutar ahora)

1. Desinstalar módulo (mismo comando shell o UI).
2. Reiniciar contenedor Odoo PROD.
3. Verificar **Cotización en PDF** estándar funciona.
4. Si hubo cambio de action por defecto (fase oficial), revertir XML en `hellenia_reports` / `sale` desde git.
5. Restaurar backup BD solo si hubo corrupción de datos (improbable — módulo solo reporte).

**Tiempo estimado rollback:** < 15 minutos sin cambio de formato oficial.

---

## 12. Pasos exactos para migrar a PROD (reporte paralelo)

> ⛔ **NO EJECUTAR** hasta aprobación visual + autorización escrita.

### Pre-requisitos

- [ ] VIS-001 resuelto o aceptado explícitamente por responsable
- [ ] Aprobación visual firmada (Fausto)
- [ ] Backup BD PROD verificado
- [ ] Ventana de mantenimiento acordada (opcional)

### Despliegue

```bash
# 1. En VPS PROD — copiar solo el módulo (NO evidence/ ni scripts test)
cd /opt/odoo-projects/hellenia
git fetch && git checkout <rama-release>
# Verificar: solo custom/justech_report_design/

# 2. Cargar variables PROD
source config/prod/.env
cd docker/prod

# 3. Instalar o actualizar módulo
docker compose --env-file ../../config/prod/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" \
  --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -i justech_report_design --stop-after-init --no-http

# Si ya instalado:
# ... -u justech_report_design --stop-after-init --no-http

# 4. Reiniciar Odoo
docker compose --env-file ../../config/prod/.env up -d --force-recreate odoo
```

### Validación post-PROD

- [ ] Módulo **Instalado** en Aplicaciones
- [ ] Menú Imprimir muestra **Cotización Hellenia (Diseño)**
- [ ] Reporte estándar **Cotización en PDF** sigue funcionando
- [ ] PDF 1 y 5+ productos — diseño, logo, totales, footer
- [ ] Factura, compra, picking — sin regresión
- [ ] Logs sin error QWeb

---

## 13. Pasos para convertirlo en formato OFICIAL de cotización

> Requiere fase adicional autorizada (24.1H o similar). **NO hacer en esta auditoría.**

### Opción A — Reemplazar action estándar (recomendada tras OK visual)

1. En `justech_report_design` o módulo puente:
   - Heredar `sale.action_report_saleorder` y cambiar `report_name` → `justech_report_design.report_hellenia_quotation_document`
   - O desactivar binding del action paralelo y reutilizar el xml id estándar
2. Desactivar/retirar herencias de cotización en `hellenia_reports` (`report_sale_quotation.xml`, `report_sale_order.xml`) para evitar triple diseño.
3. Actualizar `-u` en PROD.
4. Validar que **Imprimir → Cotización** (único) genera diseño Justech.
5. Comunicar a usuarios el cambio de formato único.

### Opción B — Mantener paralelo pero predeterminado

1. Configurar secuencia/permiso para ocultar reportes legacy en UI (menos invasivo).
2. Capacitar: usar solo **Cotización Hellenia (Diseño)**.

### Criterios de aceptación formato oficial

- [ ] VIS-001 cerrado
- [ ] Aprobación visual 1:1 con referencia HTML/CSS
- [ ] Un solo diseño de cotización en producción (sin confusión)
- [ ] Portal (si aplica) definido en fase posterior

---

## 14. Cómo revertir si falla en PROD

| Situación | Acción |
|-----------|--------|
| PDF JT corrupto / error QWeb | `-u justech_report_design` con versión anterior git, o desinstalar |
| Usuarios confundidos con dos reportes | Desinstalar JT; seguir con estándar + hellenia_reports |
| Se cambió action estándar y falla | `git revert` del commit que modificó `sale.action_report_saleorder`; `-u sale,hellenia_reports` |
| Estilos no cargan | Reinicio Odoo + limpiar assets; verificar `addons_path` |

```bash
# Rollback rápido — desinstalar (PROD)
source config/prod/.env && cd docker/prod
docker compose --env-file ../../config/prod/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http <<'PY'
env['ir.module.module'].search([('name','=','justech_report_design')]).button_immediate_uninstall()
PY
docker compose --env-file ../../config/prod/.env restart odoo
```

---

## 15. Checklist de promoción PROD (preparado — NO ejecutar)

Ver también: `packages/phase24-1-hellenia-quotation-review/PROD_PROMOTION_CHECKLIST.md`

- [ ] Aprobación visual Fausto / responsable
- [ ] VIS-001 resuelto o waiver documentado
- [ ] `audit.json` reciente con todas las secciones PASS
- [ ] Autorización escrita: promover a PROD
- [ ] Backup BD PROD
- [ ] Merge rama a release acordada
- [ ] Diff revisado: solo `custom/justech_report_design/`
- [ ] Sin override no autorizado de `sale.report_saleorder_document`
- [ ] Instalar en PROD (`-i` o `-u`)
- [ ] Validación post-despliegue (cotización + regresión factura/compra/stock)
- [ ] Registro en tabla de promoción (fecha, ejecutor, versión)

---

## 16. Comandos preparados (NO ejecutados en PROD)

### Instalación / actualización TEST (referencia — ya aplicado)

```bash
source /opt/odoo-projects/hellenia/config/test/.env
cd /opt/odoo-projects/hellenia/docker/test
docker compose --env-file ../../config/test/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_report_design --stop-after-init --no-http
```

### Auditoría TEST

```bash
bash scripts/run-phase24-1g-audit.sh
# Evidencia: evidence/phase24-1g-audit/audit.json
```

### Rollback TEST

```bash
docker compose ... exec odoo odoo shell -d hellenia_test ... <<'PY'
env['ir.module.module'].search([('name','=','justech_report_design')]).button_immediate_uninstall()
PY
```

---

## 17. Comparación antes / después

| Aspecto | Antes (solo estándar + hellenia_reports) | Después (con justech_report_design en TEST) |
|---------|------------------------------------------|---------------------------------------------|
| Reporte por defecto cotización | `sale.report_saleorder` + herencias xpath `hellenia_reports` | **Sin cambio** — mismo estándar |
| Nuevo menú Imprimir | — | **Cotización Hellenia (Diseño)** |
| Layout PDF JT | — | `web.html_container` + SCSS dedicado |
| Paperformat | Estándar empresa | `Hellenia Quotation Paperformat` (Letter 90 DPI) |
| Condiciones | Texto fijo / herencia legacy | `note` editable + fallback `_JT_DEFAULT_TERMS` |
| Descuentos en PDF | Según herencia legacy | Columna DESC. condicional + desglose totales |
| Firmas | Tablas/cajas legacy | Divs + spacer dinámico (`get_jt_quotation_signature_push_px`) |
| Facturas / compras / stock | Baseline | **Idéntico** — sin reportes JT |
| Portal cotización JT | — | No implementado (HTML en URL pública) |

---

## 18. Conclusión

El módulo `justech_report_design` en TEST cumple los requisitos **técnicos y funcionales** de la auditoría 24.1G:

- No rompe `sale.report_saleorder`, `sale.report_saleorder_document` ni `sale.report_saleorder_raw`.
- Opera en **paralelo** sin reemplazar el formato estándar.
- Dependencias, campos, escenarios y PDF backend validados con **PASS**.
- No impacta facturas, pagos, compras, inventario ni DGII.

**No está listo para migrarse como formato oficial** debido a:

1. **VIS-001** (issue visual bloqueante).
2. **Aprobación visual** pendiente del responsable.
3. Falta de **decisión y fase de reemplazo** del action estándar (pasos documentados en §13, no ejecutados).

**Recomendación:** Resolver VIS-001 y obtener OK visual → promover a PROD como reporte **paralelo** → tras periodo de uso estable, ejecutar fase de **oficialización** (§13) con rollback plan listo (§14).

---

*Generado por auditoría Fase 24.1G — Cloud Agent. PROD no modificado.*
