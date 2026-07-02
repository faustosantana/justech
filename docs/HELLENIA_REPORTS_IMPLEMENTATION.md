# Implementación Formatos Corporativos — hellenia_reports

**Fase:** 13.6  
**Cliente:** Hellenia, S.R.L.  
**Módulo:** `custom/hellenia_reports` v19.0.1.0.0  
**Fecha:** 2026-06-30  
**Estado:** **IMPLEMENTADO Y DESPLEGADO**

---

## 1. Resumen

Se implementó el módulo `hellenia_reports` con formatos visuales corporativos para documentos comerciales, usando herencia QWeb upgrade-safe. Sin modificar core, Enterprise ni `odoo-pecv`.

| Ambiente | Módulo | Layout | Resultado |
|----------|--------|--------|-----------|
| TEST | `installed` | `external_layout_hellenia` | **PASS** |
| PROD | `installed` | `external_layout_hellenia` | **PASS** |

**Backup PROD previo:** `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-06-30_1641`

---

## 2. Componentes implementados

### 2.1 Layout corporativo

| Componente | XML ID | Descripción |
|------------|--------|-------------|
| Layout principal | `hellenia_reports.external_layout_hellenia` | Encabezado, pie, logo, RNC, contacto |
| Registro layout | `hellenia_reports.report_layout_hellenia` | Selector en configuración documentos |
| Paperformat | `hellenia_reports.paperformat_hellenia_letter` | Carta US Letter, márgenes Hellenia |
| Bloques pie | `hellenia_reports.hellenia_document_footer_blocks` | Términos, firma, sello |

### 2.2 Documentos personalizados

| Documento | Herencia | Archivo |
|-----------|----------|---------|
| Cotización / pedido venta | `sale.report_saleorder_document` | `report/report_sale_order.xml` |
| Factura / NC | `account.report_invoice_document` | `report/report_invoice.xml` |
| RFQ / OC | `purchase.report_purchasequotation_document` | `report/report_purchase.xml` |
| | `purchase.report_purchaseorder_document` | |
| Entrega / recepción | `stock.report_delivery_document` | `report/report_stock.xml` |
| Picking almacén | `stock.report_picking` | |

### 2.3 Modelos extendidos

| Modelo | Campos nuevos |
|--------|---------------|
| `res.company` | colores, términos, aviso legal, firma, sello, redes, QR |
| `account.move` | `hellenia_invoice_qr_uri()` para QR en facturas |

### 2.4 Estilos

- `static/src/scss/hellenia_reports.scss` — registrado en `web.report_assets_common`
- Paleta: azul marino `#1a365d`, dorado `#c9a227`
- Tablas con encabezado corporativo, NCF destacado en caja

---

## 3. Dependencias

```python
"depends": [
    "hellenia_base",
    "sale", "account", "purchase", "stock",
    "justech_l10n_do_ncf",
]
```

---

## 4. Instalación

```bash
# TEST
scripts/install-hellenia-reports.sh test
scripts/run-phase13-6-validate-reports.sh test

# PROD (tras PASS TEST + backup)
scripts/backup-hellenia-prod.sh
scripts/install-hellenia-reports.sh prod
scripts/run-phase13-6-validate-reports.sh prod
```

---

## 5. Configuración empresa

**Configuración → Empresas → Documentos Hellenia:**

- Colores primario/secundario
- Términos y condiciones (HTML)
- Aviso legal facturas
- Firma y sello (imágenes)
- Redes sociales
- Mostrar QR en facturas

**Ya configurado en PROD/TEST:**

| Campo | Valor |
|-------|-------|
| Empresa | Hellenia, S.R.L. |
| RNC | 133621282 |
| Logo | Sí |
| Teléfono | +1 849-434-8694 |
| Email | info@helleniadr.com |
| Web | https://hellenia.cloud |

---

## 6. Integración fiscal

- NCF destacado en caja corporativa (reemplaza bloque duplicado de `justech_l10n_do_ncf`)
- QR opcional con valor NCF
- ITBIS 18% sin cambios — hereda cálculo estándar + fiscal Justech

---

## 7. Evidencia

| Archivo | Ambiente |
|---------|----------|
| `evidence/phase13-6-hellenia-reports-test.json` | TEST |
| `evidence/phase13-6-hellenia-reports-prod.json` | PROD |

---

## 8. Referencias

- [HELLENIA_PDF_UAT_REPORT.md](HELLENIA_PDF_UAT_REPORT.md)
- [HELLENIA_BRANDING_REPORT.md](HELLENIA_BRANDING_REPORT.md)
- [REPORT_ENGINE_ARCHITECTURE.md](REPORT_ENGINE_ARCHITECTURE.md)
