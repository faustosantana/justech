# PDF Visual Certification — Fase 23

**Proyecto:** Hellenia Odoo 19 Enterprise  
**Rama:** `cursor/phase23-corporate-identity-dd85`  
**Módulo:** `hellenia_reports` 19.0.1.1.0  
**Fecha:** 2026-06-29

---

## 1. Objetivo de certificación

Verificar que todos los documentos PDF comparten la misma identidad visual corporativa Hellenia (`#3E4827`, fondos blancos, tipografía unificada).

---

## 2. Checklist de consistencia

| Criterio | Esperado | Estado |
|----------|----------|--------|
| Color primario `#3E4827` en headers/tablas | Sí | PASS (TEST) |
| Sin azul ni dorado | Sí | PASS |
| Layout `external_layout_hellenia` | Todos los comerciales | PASS |
| Paperformat `Hellenia Carta` | Todos los reportes | PASS |
| Etiquetas en español | 100% | PASS |
| NCF → "Número de Comprobante Fiscal" | Facturas | PASS |
| Leyenda DGII bajo NCF | Facturas | PASS |
| Sin QR en factura | Sí | PASS |
| Recibo con retenciones detalladas | Sí | Implementado (sin pago posted en TEST) |
| NC/ND misma familia que factura | Sí | PASS |
| Delivery slip rediseñado | Sí | PASS |
| Estados de cuenta estilizados | Sí | PASS |

---

## 3. Documentos a generar

| # | Documento | Archivo ejemplo | Fuente datos |
|---|-----------|-----------------|--------------|
| 01 | Cotización | `01_cotizacion.pdf` | `sale.order` draft/sent |
| 02 | Factura | `02_factura.pdf` | `account.move` out_invoice posted |
| 03 | Nota de crédito | `03_nota_credito.pdf` | `account.move` out_refund |
| 04 | Nota de débito | `04_nota_debito.pdf` | B03 posted |
| 05 | Orden de compra | `05_orden_compra.pdf` | `purchase.order` purchase |
| 06 | RFQ | `06_rfq.pdf` | `purchase.order` draft/sent |
| 07 | Delivery slip | `07_delivery_slip.pdf` | `stock.picking` outgoing done |
| 08 | Recepción | `08_recepcion.pdf` | `stock.picking` incoming |
| 09 | Recibo de pago | `09_recibo_pago.pdf` | `account.payment` posted |
| 10 | Estado cuenta cliente | `10_estado_cuenta_cliente.pdf` | `res.partner` followup |
| 11 | Estado cuenta proveedor | `11_estado_cuenta_proveedor.pdf` | `account_reports` export |

---

## 4. Script de generación

```bash
# En servidor Odoo (TEST o PROD)
docker exec hellenia-test-odoo-1 odoo shell -d hellenia_test --no-http < scripts/phase23-generate-sample-pdfs.py
```

Salida: `/tmp/phase23-sample-pdfs/` + `evidence.json`

---

## 5. Comparación visual

Tras generar los PDFs, verificar:

1. **Encabezado:** mismo logo, tipografía y línea verde en todos
2. **Títulos:** mismo estilo `hellenia-doc-title` (mayúsculas, borde inferior)
3. **Tablas:** cabecera verde `#3E4827`, filas alternas consistentes
4. **Pie:** línea verde + paginación + aviso legal
5. **Márgenes:** uniformes en carta vertical
6. **Sin regresiones:** no aparecen colores azul/dorado heredados de Bootstrap

---

## 6. Inconsistencias conocidas / mitigaciones

| Issue | Mitigación |
|-------|------------|
| SCSS anterior usaba `#1a365d` y `#c9a227` | Reemplazado por `#3E4827` |
| Bloque NCF duplicado justech | Oculto vía herencia QWeb |
| Recibo duplicaba retenciones | Cleanup de template `hellenia_account` |
| account_reports usa SCSS propio | Override vía `hellenia-account-report-pdf` |

---

## 7. Evidencia

| Artefacto | Ubicación |
|-----------|-----------|
| PDFs ejemplo | `evidence/phase23-sample-pdfs/` |
| JSON certificación | `evidence/phase23-sample-pdfs/evidence.json` |
| Design system | `docs/HELLENIA_DESIGN_SYSTEM.md` |
| Guidelines | `docs/CORPORATE_DOCUMENT_GUIDELINES.md` |

---

## 8. Resultado

| Entorno | Fecha | Resultado | Notas |
|---------|-------|-----------|-------|
| TEST | 2026-07-01 | PASS (10/11 PDFs) | Recibo de pago SKIP — sin pagos posted en TEST |
| PROD | No promovido | — | Esperar certificación visual TEST |

**Criterio de promoción:** Todos los PDFs generados sin error + revisión visual PASS en checklist §5.
