# Fase 6.5 — Revisión Fiscal

**Normativa referencia:** DGII República Dominicana — NCF serie B (tradicional)  
**Fecha:** 2026-06-30

---

## 1. Resumen

Cobertura fiscal **MVP funcional** para emisión B01/B02/B04/B11/B13 y reportes básicos. **No cumple** formato oficial DGII para envío. Trazabilidad parcial vía `consumption`. Gaps en B03, B13, devoluciones compra, y validación RNC DGII.

**Calificación fiscal:** **A-**

---

## 2. Tipos NCF implementados

| Prefijo | Caso | Auto-asign | Validado DEV | Validado unit |
|---------|------|------------|--------------|---------------|
| B01 | Crédito fiscal (RNC) | ✅ | ✅ | ✅ |
| B02 | Consumo final | ✅ | ✅ | ✅ |
| B03 | Nota débito | ✅ lógica | ❌ | ❌ |
| B04 | Nota crédito | ✅ | ✅ | ✅ |
| B11 | Compras | ✅ | ✅ | ✅ |
| B13 | Gastos menores | ✅ | ✅ E2E | ❌ unit |

---

## 3. Trazabilidad

| Evento | Registro | Completo |
|--------|----------|----------|
| Emisión NCF | `justech.do.ncf.consumption` (consumed) | ✅ |
| Rango usado | `justech_do_ncf_range_id` en move | ✅ |
| Tipo documento | `justech_do_document_type_id` | ✅ |
| NC referencia | `justech_do_origin_ncf` en refund | ✅ si `reversed_entry_id` |
| Anulación | `justech_do_ncf_voided` + consumption voided | ✅ |
| Motivo anulación | `justech_do_ncf_void_reason` | ⚠️ Opcional, sin UI obligatoria |
| Autorización DGII | `authorization_number` en rango | ⚠️ Capturado, no validado |

**No hay `mail.thread`** — historial de cambios en rangos no auditado en chatter.

---

## 4. Integridad NCF

| Control | Implementado | Gap |
|---------|--------------|-----|
| Formato 11 chars | ✅ regex `^[BE][0-9]{2}[0-9]{8}$` | — |
| Duplicado posted | ✅ search + constraint | Drafts pueden duplicar |
| Rango agotado | ✅ state depleted | — |
| Rango vencido | ✅ state expired | Sin cron automático |
| Secuencia ordenada | ✅ next_sequence | Sin lock concurrente |
| NCF manual compra proveedor | ⚠️ Parcial | Solo auto B11/B13 |

---

## 5. Flujos por tipo de documento

### Factura cliente (B01/B02)

```
partner.vat? → B01 : B02
→ range → consume → post → PDF con NCF
```
✅ Correcto MVP

### Nota crédito (B04)

```
_reverse_moves → out_refund → B04 + origin_ncf
```
✅ Correcto

### Nota débito (B03)

```
out_invoice + debit_origin_id → B03
```
⚠️ Sin prueba; depende `account_debit_note`

### Compra (B11/B13)

```
journal.default_document_type → auto NCF
```
⚠️ Compras normales con NCF **manual del proveedor** no tienen flujo dedicado

### Devolución compra (`in_refund`)

**Sin lógica NCF** — gap fiscal

### Pagos / cobros

NCF permanece en factura origen — ✅ correcto (NCF no cambia en pago)

---

## 6. Reportes DGII

| Reporte | Generación | Formato oficial | Export |
|---------|------------|-----------------|--------|
| 606 | ✅ Básico | ❌ No TXT DGII | CSV/XLSX |
| 607 | ✅ Básico | ❌ No TXT DGII | CSV/XLSX |
| 608 | ✅ Voided | ❌ No TXT DGII | CSV/XLSX |

### Problemas reportes

1. ITBIS por nombre impuesto `"ITBIS"` — frágil
2. 606 incluye `in_refund` sin lógica NCF específica
3. 608 filtra por `invoice_date` en dominio base pero usa `void_date` en línea — inconsistencia período
4. Sin validación de totales vs libro mayor

---

## 7. Validación RNC

- Formato 9-11 dígitos ✅
- **Sin algoritmo de dígito verificador DGII** ❌
- Sin consulta WS DGII (fuera MVP — correcto)

---

## 8. Matriz trazabilidad fiscal-contable

| Documento | NCF | Asiento | Consumo audit | Reporte |
|-----------|-----|---------|---------------|---------|
| out_invoice | ✅ | ✅ estándar | ✅ | 607 |
| out_refund | ✅ | ✅ estándar | ✅ | 607 |
| in_invoice B11/B13 | ✅ | ✅ estándar | ✅ | 606 |
| in_invoice normal | ⚠️ manual | ✅ | ⚠️ | 606 |
| in_refund | ❌ | ✅ | ❌ | 606? |
| void NCF | ✅ voided | ✅ sin reversar | ✅ voided | 608 |

---

## 9. Recomendaciones fiscales

### P0
1. Lock secuencia NCF (integridad DGII)
2. Obligar `void_reason` en anulación
3. Record rules multi-empresa

### P1
4. Flujo NCF manual en compras con validación proveedor
5. B03 E2E + documentación
6. `in_refund` con tipo NCF apropiado
7. Formato TXT DGII (fase posterior dedicada)

### P2
8. Validación dígito verificador RNC
9. Cron expiración rangos
10. Alertas `ncf_alert_days` (campo ya existe)

---

## 10. Conclusión

Fiscalmente **operable para piloto Hellenia** con NCF tradicional básico. **No certificable** como cumplimiento DGII completo ni producto fiscal genérico sin cerrar gaps B03, compras, concurrencia y formato oficial.

**Calificación:** **A-**
