# Backlog de campos faltantes — DGII / Justech Localization RD

**Fase:** 17.5  
**Fecha:** 2026-06-30  
**Política:** No se inventaron campos. Solo se listan campos requeridos por DGII que **no existen** en Odoo estándar ni están verificables en este repositorio JAIOS.

**Campos Odoo estándar utilizables hoy** (sin desarrollo):

- `res.partner.vat`, `res.partner.name`
- `res.company.vat`
- `account.move.name`, `ref`, `invoice_date`, `invoice_date_due`
- `account.move.amount_untaxed`, `amount_tax`, `amount_total`, `amount_residual`
- `account.move.move_type`, `state`, `payment_state`
- `account.payment.date`, `amount`
- `account.move.line.tax_ids`, `balance`

**Referencias Hellenia (Odoo TEST, no en este repo):**

- `hellenia.withholding.catalog` — catálogo retenciones Fase 18
- Líneas de retención en pagos/facturas (motor Fase 17–18)

---

## Campos críticos (bloquean 606/607/608)

| Campo propuesto | Formatos | Descripción DGII | Prioridad |
|-----------------|----------|------------------|-----------|
| `justech_do_ncf` | 606, 607, 608, ITBIS, Norma 2-05 | Número Comprobante Fiscal emitido/recibido | **P0** |
| `justech_do_partner_id_type` | 606, 607, Norma 2-05 | Tipo identificación: 1=RNC, 2=Cédula, 3=Pasaporte | **P0** |
| `justech_do_ncf_modified` | 606, 607 | NCF de documento modificado (NC/ND) | **P0** |
| `justech_do_dgii_line_status` | 606, 607, 608, 609 | Estatus línea DGII (1=válido, 2=anulado) | **P0** |
| `justech_do_ncf_cancel_type` | 608 | Tipo de anulación (códigos 01–10) | **P0** |

---

## Campos compras (606)

| Campo propuesto | Descripción | Prioridad |
|-----------------|-------------|-----------|
| `justech_do_expense_type_606` | Tipo bienes y servicios comprados (catálogo 01–11) | **P1** |
| `justech_do_payment_method_dgii` | Forma de pago DGII (01–07) | **P1** |
| `justech_do_itbis_proportionality` | ITBIS proporcionalidad Art. 349 | P2 |
| `justech_do_itbis_cost` | ITBIS llevado al costo | P2 |
| `justech_do_itbis_advance` | ITBIS por adelantar | P2 |
| `justech_do_itbis_perceived_purchase` | ITBIS percibido en compras | P2 |
| `justech_do_isr_perceived_purchase` | ISR percibido en compras | P2 |
| `justech_do_isc_amount` | Impuesto selectivo al consumo | P2 |
| `justech_do_legal_tip` | Monto propina legal | P3 |

**Nota:** Montos servicios vs bienes (cols K/L) pueden derivarse de `account.move.line` por `product_id.type` si se define regla de clasificación.

---

## Campos ventas (607)

| Campo propuesto | Descripción | Prioridad |
|-----------------|-------------|-----------|
| `justech_do_income_type_607` | Tipo de ingreso (01–06) | **P1** |
| `justech_do_sale_payment_breakdown` | Desglose formas de venta (cols R–X) | **P1** |
| `justech_do_withholding_date` | Fecha de retención | P2 |
| `justech_do_itbis_withheld_by_third` | ITBIS retenido por terceros | P2 |
| `justech_do_itbis_perceived_sale` | ITBIS percibido | P2 |
| `justech_do_isr_withheld_by_third` | Retención renta por terceros | P2 |
| `justech_do_isr_perceived_sale` | ISR percibido | P2 |

**Nota:** `justech_do_sale_payment_breakdown` puede modelarse como JSON o 7 campos monetarios en `account.move` o en líneas de pago.

---

## Campos pagos al exterior (609)

| Campo propuesto | Descripción | Prioridad |
|-----------------|-------------|-----------|
| `justech_do_foreign_id_type` | Tipo ID tributaria extranjera | **P1** |
| `justech_do_country_dgii_code` | Código país DGII (hoja Listas) | **P1** |
| `justech_do_foreign_service_type` | Tipo servicio adquirido | **P1** |
| `justech_do_related_party` | Parte relacionada (1=Sí, 2=No) | **P1** |
| `justech_do_isr_withholding_date` | Fecha retención ISR | P2 |
| `justech_do_presumed_income` | Renta presunta | P2 |

---

## Campos retenciones del Estado (623)

| Campo propuesto | Descripción | Prioridad |
|-----------------|-------------|-----------|
| `justech_do_state_entity_rnc` | RNC entidad gubernamental retenedora | **P1** |
| `justech_do_state_withholding_date` | Fecha de retención | **P1** |
| `justech_do_state_reference_number` | Número de referencia | **P1** |
| `justech_do_state_reference_type` | Tipo de referencia (catálogo DGII) | **P1** |
| `justech_do_state_withholding_bank` | Banco | P2 |

**Integración:** relacionar con retención `RET-GOB-5` del catálogo `hellenia.withholding.catalog` (TEST).

---

## Campos ITBIS adelantos

### LOCAL (compras)

| Campo | Estado |
|-------|--------|
| Proveedor, fecha, montos | Cubierto por Odoo estándar |
| NCF en número factura | **Falta** `justech_do_ncf` |
| Bien/Servicio (descripción) | Cubierto por líneas de factura |

### IMPORTACION (aduanas)

| Campo propuesto | Descripción | Prioridad |
|-----------------|-------------|-----------|
| `justech_do_customs_office` | Colecturía | **P2** |
| `justech_do_import_declaration_date` | Fecha declaración | **P2** |
| `justech_do_import_receipt_number` | No. recibo | **P2** |
| `justech_do_import_form_number` | Planilla | **P2** |
| `justech_do_import_liquidation_number` | Liquidación | **P2** |
| `justech_do_import_cif_amount` | Monto CIF RD$ | **P2** |
| `justech_do_import_fob_amount` | Monto FOB RD$ | **P2** |
| `justech_do_import_itbis_amount` | Monto ITBIS RD$ | **P2** |

**Nota:** IMPORTACION típicamente requiere módulo aduanero o entrada manual; no existe en Odoo estándar.

---

## Campos Norma 2-05

| Campo | Estado |
|-------|--------|
| RNC, fecha, montos | Parcialmente cubierto |
| Tipo identificación | **Falta** `justech_do_partner_id_type` |
| NCF | **Falta** `justech_do_ncf` |
| Identificacion Retención | **Falta** `dgii_withholding_code` en `hellenia.withholding.catalog` |

**Acción Fase 19 sugerida:** agregar columna `dgii_code` / `dgii_withholding_code` al catálogo de retenciones mapeando RET-ITBIS-30, RET-ITBIS-100, RET-INF-ITBIS-75, etc.

---

## Resumen por prioridad

| Prioridad | Campos únicos | Impacto |
|-----------|---------------|---------|
| **P0** | 5 | Desbloquea 606, 607, 608 |
| **P1** | 12 | Desglose pagos, clasificaciones, 609, 623 |
| **P2** | 15+ | ITBIS avanzado, percepciones, importaciones |
| **P3** | 1 | Propina legal |

---

## Reglas para futuras fases

1. **No implementar exportadores** hasta tener al menos P0 en módulo `justech_l10n_do_*` en repo Odoo/Hellenia.
2. Validar nombres de campos contra módulos reales antes de codificar — este backlog usa prefijo `justech_do_` como convención propuesta.
3. Actualizar este documento cuando se implemente cada campo en Odoo TEST.
4. No promover a PROD sin validación contra plantillas DGII vigentes.
