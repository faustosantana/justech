# UAT PDF — Formatos Corporativos Hellenia

**Fase:** 13.6  
**Fecha:** 2026-06-30  
**Validador:** Script automatizado `phase13-6-validate-hellenia-reports.py`

---

## 1. Resultado global

| Ambiente | Resultado | Errores | Advertencias |
|----------|-----------|---------|--------------|
| **TEST** (`hellenia_test`) | **PASS** | 0 | 0 |
| **PROD** (`hellenia_prod`) | **PASS** | 0 | 0 |

---

## 2. Checklist UAT

| # | Criterio | TEST | PROD |
|---|----------|------|------|
| 1 | Módulo `hellenia_reports` instalado | ✅ | ✅ |
| 2 | Layout `external_layout_hellenia` activo | ✅ | ✅ |
| 3 | Paperformat `Hellenia Carta` | ✅ | ✅ |
| 4 | PDF cotización | ✅ 51 KB | ✅ 65 KB |
| 5 | PDF pedido venta | ✅ 51 KB | ✅ 65 KB |
| 6 | PDF factura | ✅ 58 KB | ✅ 65 KB |
| 7 | PDF nota de crédito | ✅ 56 KB | ✅ 64 KB |
| 8 | PDF RFQ compra | ✅ 52 KB | ✅ 64 KB |
| 9 | PDF orden de compra | ✅ 55 KB | ✅ 66 KB |
| 10 | PDF entrega | ✅ 45 KB | ✅ 59 KB |
| 11 | PDF recepción | ✅ 47 KB | ✅ 60 KB |
| 12 | NCF en factura | ✅ B0200020113 | ✅ B0200009903 |
| 13 | ITBIS 18% en factura | ✅ | ✅ |
| 14 | Logo empresa | ✅ | ✅ |
| 15 | RNC en encabezado | ✅ 133621282 | ✅ 133621282 |

---

## 3. Validación por documento

### 3.1 Ventas

| Documento | XML ID | TEST | PROD |
|-----------|--------|------|------|
| Cotización | `sale.report_saleorder` | PASS | PASS |
| Pedido venta | `sale.report_saleorder` | PASS | PASS |

**Verificado:** títulos en español, tabla corporativa, layout Hellenia.

### 3.2 Contabilidad

| Documento | XML ID | TEST | PROD |
|-----------|--------|------|------|
| Factura | `account.account_invoices` | PASS | PASS |
| Nota de crédito | `account.account_invoices` | PASS | PASS |

**Verificado:** NCF en caja destacada, QR generado, ITBIS 18%.

### 3.3 Compras

| Documento | XML ID | TEST | PROD |
|-----------|--------|------|------|
| RFQ | `purchase.report_purchasequotation` | PASS | PASS |
| Orden de compra | `purchase.report_purchaseorder` | PASS | PASS |

### 3.4 Inventario

| Documento | XML ID | TEST | PROD |
|-----------|--------|------|------|
| Entrega | `stock.report_deliveryslip` | PASS | PASS |
| Recepción | `stock.report_deliveryslip` | PASS | PASS |

---

## 4. Validación visual (pendiente cliente)

Los PDFs se generan correctamente. La aprobación estética final requiere revisión humana de Hellenia:

| Aspecto | Estado automatizado | Revisión manual |
|---------|---------------------|-----------------|
| Márgenes carta | ✅ Paperformat aplicado | Pendiente |
| Paginación tablas largas | ✅ Sin error render | Pendiente |
| Legibilidad fuentes | ✅ DejaVu | Pendiente |
| Alineación logo | ✅ Logo presente | Pendiente |
| Colores corporativos | ✅ SCSS aplicado | Confirmar con marca |

---

## 5. Observaciones técnicas

| Observación | Impacto |
|-------------|---------|
| Secuencia picking TEST desincronizada | Bajo — script usa PO existente |
| `ContentNotFoundError` ocasional wkhtmltopdf | Bajo — PDF se genera |
| Términos/firma/sello no configurados aún | Visual — campos vacíos hasta que Hellenia los cargue |

---

## 6. Conclusión UAT

**TEST: PASS** — Todos los documentos generan PDF corporativo válido.  
**PROD: PASS** — Promoción autorizada tras validación TEST.

**Documentos listos para entrega al cliente:** **Sí, con observaciones visuales** — funcionalidad completa; pendiente carga de términos legales, firma y sello, y UAT visual por Hellenia.

---

## 7. Evidencia

- `evidence/phase13-6-hellenia-reports-test.json`
- `evidence/phase13-6-hellenia-reports-prod.json`
