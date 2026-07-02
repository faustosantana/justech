# Fase 23.2 — Promoción a Producción Identidad Visual Hellenia

**Fecha:** 2026-07-01  
**Entorno:** `hellenia_prod` @ https://odoo.hellenia.cloud  
**Módulo:** `hellenia_reports` **19.0.1.0.1 → 19.0.1.1.0**  
**Rama origen:** `cursor/phase23-corporate-identity-dd85`  
**Resultado:** **PROD PASS — 11/11 PDFs certificados**

---

## 1. Resumen ejecutivo

Se promovió a producción la identidad visual corporativa Hellenia (`#3E4827`) certificada en TEST, actualizando únicamente el módulo `hellenia_reports` (QWeb, SCSS, layouts PDF). No se modificó lógica de pagos, retenciones, conciliación, DGII, NCF ni contabilidad.

---

## 2. Backup

| Campo | Valor |
|-------|-------|
| **Backup usado** | `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-01_1753` |
| PostgreSQL | `postgres_all.sql.gz` (3.4 MB) |
| Filestore | `filestore.tar.gz` (4.4 MB) |
| Custom | `custom.tar.gz` (231 KB) |
| Config | `docker-compose.yml`, `odoo.conf`, `.env`, `MANIFEST.txt` |
| Verificación | Dump PostgreSQL válido + archivos presentes |

### Rollback disponible

```bash
/opt/odoo-projects/hellenia/scripts/restore-hellenia-prod.sh \
  /opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-01_1753
```

Restaura base de datos, filestore y custom al estado pre-promoción.

---

## 3. Promoción desplegada

### 3.1 Artefactos sincronizados

- `custom/hellenia_reports/` completo desde rama `cursor/phase23-corporate-identity-dd85`
- Versión manifest: **19.0.1.1.0**

### 3.2 Procedimiento de upgrade

```bash
docker stop hellenia-prod-odoo-1
docker run --rm --network hellenia-prod_default \
  -v hellenia-prod_odoo-data:/var/lib/odoo \
  -v /opt/odoo-projects/hellenia/enterprise:/mnt/enterprise:ro \
  -v /opt/odoo-projects/hellenia/custom:/mnt/custom:ro \
  -v /opt/odoo-projects/hellenia/config/production/odoo.conf:/etc/odoo/odoo.conf:ro \
  -e HOST=db -e USER=odoo -e PASSWORD=*** \
  odoo:19.0-20260619 \
  odoo -d hellenia_prod -u hellenia_reports --stop-after-init \
  --db_host=db --db_user=odoo --db_password=***
docker start hellenia-prod-odoo-1
```

### 3.3 Post-deploy

- Contenedor `hellenia-prod-odoo-1`: **healthy**
- Módulo verificado: `hellenia_reports` **19.0.1.1.0** instalado

---

## 4. Certificación PDF PROD (11/11)

| # | Documento | Registro PROD | PDF | Estado |
|---|-----------|---------------|-----|--------|
| 01 | Cotización | S00020 | `01_cotizacion.pdf` | OK |
| 02 | Factura | INV/2026/00006 (P21) | `02_factura.pdf` | OK |
| 03 | Nota de crédito | Draft NC P23-VISUAL-PDF-NC | `03_nota_credito.pdf` | OK |
| 04 | Nota de débito | Draft ND P23-VISUAL-PDF-ND | `04_nota_debito.pdf` | OK |
| 05 | Orden de compra | P00008 | `05_orden_compra.pdf` | OK |
| 06 | RFQ | P00007 | `06_rfq.pdf` | OK |
| 07 | Delivery slip | WH/OUT/00008 | `07_delivery_slip.pdf` | OK |
| 08 | Recepción | WH/IN/00003 | `08_recepcion.pdf` | OK |
| 09 | Recibo de pago | PBNKD/2026/00003 (ret. RD$500) | `09_recibo_pago.pdf` | OK |
| 10 | Estado cuenta cliente | P21 GOV PROOF UNIQUE | `10_estado_cuenta_cliente.pdf` | OK |
| 11 | Estado cuenta proveedor | P23-VISUAL-PDF Proveedor | `11_estado_cuenta_proveedor.pdf` | OK |

**Evidencia:** `evidence/phase23-2-prod-pdfs/` + `evidence.json`

### Scripts de certificación

```bash
# Datos mínimos visuales (solo documentos faltantes, ref P23-VISUAL-PDF)
cat scripts/phase23-2-prod-smoke-pdf-data.py | docker exec -i hellenia-prod-odoo-1 \
  odoo shell -d hellenia_prod --no-http --db_host=db ...

# Generación y validación 11 PDFs
cat scripts/phase23-2-prod-pdf-certification.py | docker exec -i hellenia-prod-odoo-1 \
  odoo shell -d hellenia_prod --no-http --db_host=db ...
```

---

## 5. Validación visual

| Criterio | PROD |
|----------|------|
| 11/11 PDFs generados | PASS |
| Color corporativo `#3E4827` / clases `hellenia-*` | PASS |
| Sin azul `#1a365d` / dorado `#c9a227` en plantillas | PASS |
| Sin QR en factura | PASS |
| Español en etiquetas de plantilla | PASS |
| "Número de Comprobante Fiscal" (no "NCF") | PASS |
| Recibo con retenciones detalladas | PASS — PBNKD/2026/00003, RET-GOB-5 RD$500, neto RD$11,300 |

---

## 6. Datos de prueba visual (P23-VISUAL-PDF)

PROD tenía base operativa limitada (sin NC, ND, OC, RFQ, recepción). Para completar 11/11 sin tocar lógica contable/fiscal se crearon **solo borradores y documentos operativos** con referencia `P23-VISUAL-PDF`:

| Registro | Tipo | Estado | Impacto fiscal |
|----------|------|--------|----------------|
| NC id 135 | out_refund | **draft** | Ninguno (no publicada) |
| ND id 136 | out_invoice B03 | **draft** | Ninguno (no publicada) |
| P00007 | RFQ | draft | Ninguno |
| P00008 | OC | purchase | Operativo (sin factura proveedor) |
| WH/IN/00003 | Recepción | assigned | Operativo |

**No se crearon pagos nuevos en PROD.** El recibo usa el pago certificado existente `PBNKD/2026/00003` (cadena P21).

---

## 7. Observaciones visuales menores

| Hallazgo | Severidad | Notas |
|----------|-----------|-------|
| Método de pago muestra `Manual Payment` | Menor | Dato maestro Odoo en inglés; etiquetas de plantilla en español |
| NC/ND generados en borrador | Informativo | Solo para certificación PDF; no afectan DGII |

---

## 8. Módulos NO modificados

- `hellenia_account` (pagos/retenciones)
- `justech_l10n_do_reports` (DGII)
- `justech_l10n_do_ncf` (NCF)
- Lógica contable / asientos

---

## 9. Resultado final

| Métrica | Valor |
|---------|-------|
| **PROD** | **PASS** |
| Backup | `2026-07-01_1753` |
| PDFs certificados | **11/11** |
| Rollback | Disponible |
| hellenia_reports PROD | **19.0.1.1.0** |

---

## 10. Referencias

- `docs/HELLENIA_DESIGN_SYSTEM.md`
- `docs/CORPORATE_DOCUMENT_GUIDELINES.md`
- `docs/PDF_VISUAL_CERTIFICATION.md` (TEST 11/11 + PROD 11/11)
