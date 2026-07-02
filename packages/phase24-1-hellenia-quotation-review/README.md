# Fase 24.1 — Paquete de revisión: Cotización Hellenia (Diseño)

**Módulo:** `justech_report_design` v19.0.1.0.0  
**Entorno validado:** TEST (`hellenia_test` / `test.hellenia.cloud`)  
**Estado:** Aprobación visual pendiente — **NO promover a PROD**

---

## Contenido del paquete

| Archivo | Descripción |
|---------|-------------|
| `quotation_1_product.pdf` | PDF backend — 1 producto (S00134) |
| `quotation_5_products.pdf` | PDF backend — 5 productos (S00135) |
| `quotation_25_products.pdf` | PDF backend — 25 productos (S00138) |
| `quotation_1_product.png` | Vista previa pág. 1 — 1 producto |
| `quotation_5_products.png` | Vista previa pág. 1 — 5 productos |
| `quotation_25_products.png` | Vista previa pág. 1 — 25 productos |
| `hellenia_quotation_template.xml` | QWeb completo (body + document) |
| `hellenia_quotation.scss` | Estilos PDF (`web.report_assets_common`) |
| `validation.json` | Resultado validación automática TEST |
| `PROD_PROMOTION_CHECKLIST.md` | Checklist promoción PROD (no ejecutar aún) |

Descarga comprimida: `phase24-1-hellenia-quotation-review.zip` (mismo directorio padre).

---

## Cómo instalar el módulo en TEST

### Opción A — Desde el repositorio (VPS)

```bash
cd /opt/odoo-projects/hellenia
# Copiar o actualizar custom/justech_report_design desde la rama cursor/phase24-1-report-design-dd85
source config/test/.env
cd docker/test
docker compose --env-file ../../config/test/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -i justech_report_design --stop-after-init --no-http
docker compose --env-file ../../config/test/.env up -d --force-recreate odoo
```

Si ya está instalado, usar `-u justech_report_design` en lugar de `-i`.

### Opción B — Desde la UI de Odoo (TEST)

1. Asegurar que `custom/justech_report_design` existe en el servidor TEST.
2. **Ajustes → Aplicaciones → Actualizar lista de aplicaciones**.
3. Buscar **Justech Report Design**.
4. **Instalar** (o **Actualizar** si ya estaba instalado).
5. Reiniciar el contenedor Odoo si los estilos PDF no se reflejan de inmediato.

### Verificación rápida post-instalación

```bash
# En el repo local (requiere acceso SSH al VPS TEST)
bash scripts/run-phase24-1-test.sh
```

Resultado esperado: `validation.json` con `"pass": true`.

---

## Cómo imprimir el reporte

1. Ir a **test.hellenia.cloud** → **Ventas** → **Cotizaciones**.
2. Abrir cualquier cotización (ej. S00134).
3. Menú **Imprimir** (o acción ⚙️ → Imprimir).
4. Seleccionar **Cotización Hellenia (Diseño)**.

El reporte estándar sigue disponible por separado como **Cotización en PDF**.

**IDs técnicos:**

- Template: `justech_report_design.report_hellenia_quotation_document`
- Acción: `justech_report_design.action_report_hellenia_quotation`
- Paperformat: `Hellenia Quotation Paperformat` (Letter, márgenes 5/8/8/8 mm, dpi 90)

---

## Qué NO se tocó

- **Producción** — ningún cambio desplegado
- `sale.report_saleorder_document` — reporte estándar intacto
- Módulo `hellenia_reports` — sin nuevas herencias de cotización
- Facturas, pagos, retenciones, DGII, contabilidad
- Reportes de compra e inventario
- Assets web del backend/frontend (solo `web.report_assets_common` para PDF)
- HTML pegado en vistas desde la interfaz de Odoo

---

## Qué queda pendiente

| Ítem | Prioridad | Notas |
|------|-----------|-------|
| Aprobación visual explícita | Alta | Comparar PDFs/PNGs de este paquete con HTML aprobado |
| Portal PDF del reporte paralelo | Media | URL con token devuelve login HTML; no bloquea backend |
| Ajustes finos de diseño | Según feedback | Copiar HTML/CSS exacto de Fausto si difiere |
| Promoción a PROD | Bloqueada | Ver `PROD_PROMOTION_CHECKLIST.md` — no ejecutar sin OK |
| Reemplazo del reporte estándar | Futuro | Solo si se decide explícitamente post-aprobación |

---

## Validación TEST (resumen)

- **Base de datos:** `hellenia_test`
- **Resultado:** `pass: true` (único FAIL informativo: `portal_pdf`)
- **Órdenes usadas:** S00134 (1p), S00135 (5p), S00138 (25p)
- **Fecha validación:** ver `validation.json` → `timestamp_utc`

---

## Rama Git

`cursor/phase24-1-report-design-dd85`

Módulo fuente: `custom/justech_report_design/`
