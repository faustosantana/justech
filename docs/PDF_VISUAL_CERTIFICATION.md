# PDF Visual Certification — Fase 23

**Proyecto:** Hellenia Odoo 19 Enterprise  
**Rama:** `cursor/phase23-corporate-identity-dd85`  
**Módulo:** `hellenia_reports` 19.0.1.1.0  
**Fecha:** 2026-07-01 (Fase 23.1 cerrada)

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
| Recibo con retenciones detalladas | Sí | PASS (Fase 23.1) |
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
| 09 | Recibo de pago | `09_recibo_pago.pdf` | `account.payment` paid (`PBNKD/2026/00027`) |
| 10 | Estado cuenta cliente | `10_estado_cuenta_cliente.pdf` | `res.partner` followup |
| 11 | Estado cuenta proveedor | `11_estado_cuenta_proveedor.pdf` | `account_reports` export |

---

## 4. Script de generación

```bash
# Generación masiva (Fase 23)
cat scripts/phase23-generate-sample-pdfs.py | docker exec -i hellenia-test-odoo-1 \
  odoo shell -d hellenia_test --no-http --db_host=db --db_user=odoo --db_password=...

# Cierre recibo de pago (Fase 23.1)
cat scripts/phase23-1-payment-receipt-visual-test.py | docker exec -i hellenia-test-odoo-1 \
  odoo shell -d hellenia_test --no-http --db_host=db --db_user=odoo --db_password=...
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
| Método de pago "Manual Payment" en recibo | Dato maestro Odoo 19 (no plantilla); etiquetas del documento en español |

---

## 7. Fase 23.1 — Recibo de pago

**Pago de prueba:** `PBNKD/2026/00027` sobre `INV/2026/00214` (NCF `B0200020173`)

| Validación | Resultado |
|------------|-----------|
| Identidad `#3E4827` / clases `hellenia-payment-*` | PASS |
| Logo corporativo | PASS |
| Cliente | PASS — SMOKE P13.4 CF |
| Factura afectada | PASS — INV/2026/00214 |
| Número de Comprobante Fiscal | PASS — B0200020173 |
| Monto aplicado RD$11,800 | PASS |
| Retención RET-GOB-5 RD$500 | PASS |
| Neto recibido RD$11,300 | PASS |
| Usuario y fecha/hora | PASS |
| Español en etiquetas de plantilla | PASS |
| Sin QR | PASS |

**Observación menor:** el valor del método de pago muestra `Manual Payment` (nombre del registro `account.payment.method` en inglés). No es defecto de plantilla; requiere traducción de dato maestro en fase UX futura si se desea 100% español en valores.

---

## 8. Evidencia

| Artefacto | Ubicación |
|-----------|-----------|
| PDFs ejemplo | `evidence/phase23-sample-pdfs/` |
| JSON certificación | `evidence/phase23-sample-pdfs/evidence.json` |
| Design system | `docs/HELLENIA_DESIGN_SYSTEM.md` |
| Guidelines | `docs/CORPORATE_DOCUMENT_GUIDELINES.md` |

---

## 9. Resultado

| Entorno | Fecha | Resultado | Notas |
|---------|-------|-----------|-------|
| TEST Fase 23 | 2026-07-01 | PASS (10/11) | Recibo pendiente |
| TEST Fase 23.1 | 2026-07-01 | **PASS (11/11)** | Recibo `PBNKD/2026/00027` certificado |
| PROD | No promovido | — | Pendiente aprobación explícita |

**Criterio de promoción:** Todos los PDFs generados sin error + revisión visual PASS — **cumplido en TEST**.

**Listo para promover a PROD:** Sí, sujeto a aprobación explícita del cliente (sin promoción automática).
