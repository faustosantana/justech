# Trazabilidad contable — reportes DGII

**Fecha:** 2026-07-01  
**Período referencia:** 202607

---

## 606 — Compras

| Eslabón | Estado |
|---------|--------|
| Facturas proveedor posted | 0 |
| Validación período | OK — 0 documentos |
| Líneas revisión | 0 |
| Trazabilidad factura→pago→asiento | **No ejercitada** |

---

## 607 — Ventas

| Eslabón | Estado |
|---------|--------|
| Facturas jul-2026 | 3 válidas |
| NCF | B0200009903–9905 (+ anteriores jun) |
| ITBIS | Coherente en líneas impuesto |
| Retenciones cliente | No aplicadas en período actual |
| Revisión fiscal | 3 líneas cargadas |

Trazabilidad: factura posted → líneas impuesto → `validate_period_607` → revisión OK.

---

## 608 — Anulados

| Eslabón | Estado |
|---------|--------|
| NCF anulados | 0 |
| Notas crédito posted | 0 |
| Motor | OK — sin error |

**No ejercitado** con nota crédito real.

---

## 623 — Retención Gobierno 5%

### Transacción certificada P21

```
INV/2026/00006 (B0200009905)
  → Pago PBNKD/2026/00003
  → Retención RET-GOB-5 línea 19 = 500.00
  → Asiento GL línea 366 = 500.00 débito
  → justech_do_gov_withholding_amount = 500.00 (factura y pago)
  → validate_period_623: válido
  → Revisión fiscal: 1 exportable
  → Excel DGII_623_202607.xlsx (Fase 21.1)
```

### Datos legacy SMOKE (incompletos)

```
INV/2026/00003
  → Pago PBNKD/2026/00002
  → Retención RET-ITBIS-30 línea 18 = 540.00 (no es gov 5%)
  → Partner sin RNC
  → Estado fiscal: incomplete
  → No exportable en 623
```

---

## Matriz trazabilidad

| Reporte | Motor | Datos limpios | Datos legacy | Export Excel |
|---------|-------|---------------|--------------|--------------|
| 606 | OK | N/A | N/A | N/A |
| 607 | OK | OK | OK | OK (F21.1) |
| 608 | OK | N/A | N/A | N/A |
| 623 | OK | OK (P21) | 2 incompletos | OK (F21.1) |

---

## Hallazgo fiscal

Partners sin RNC en transacciones con impacto DGII: **SMOKE P13.4 CF** (5 facturas).  
No es fallo de motor; es **deuda de datos maestros**.
