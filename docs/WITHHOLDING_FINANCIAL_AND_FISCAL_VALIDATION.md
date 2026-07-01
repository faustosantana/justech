# Validación financiera y fiscal — Retenciones Fase 18.2

## Impacto contable

### Mecanismo

Las retenciones se aplican **por factura** en el wizard de pagos. Al registrar el pago:

1. Se reduce el monto transferido (banco/caja) por el total retenido.
2. Se genera línea de write-off en la **cuenta contable** de cada retención.
3. El asiento queda balanceado (débito = crédito).

### Ejemplo cobro cliente con retención

```text
Banco / Caja          Neto cobrado
Retención por cobrar      Monto retenido
    Clientes (CxC)            Total aplicado
```

### Ejemplo pago proveedor con retención

```text
Proveedores (CxP)         Total aplicado
    Banco / Caja              Neto pagado
    Retención por pagar       Monto retenido
```

### Cuentas contables

Cada retención activa obtiene su cuenta desde la repartición del impuesto `l10n_do`. Si no hay cuenta, la retención permanece **inactiva** hasta configuración manual.

| Retención | Cuenta | Origen |
|-----------|--------|--------|
| RET-GOB-5 | Cuenta ISR retención venta | `-5% ISR Gov.` |
| RET-ITBIS-30 | Cuenta ITBIS retención | `-30% ITBIS Leg.` |
| RET-INF-ISR-10 | Cuenta ISR retención compra | `-10% ISR Fee` |
| … | … | Impuesto l10n_do vinculado |

### Validaciones realizadas en TEST

- Asiento balanceado tras cobro/pago con retención
- CxC conciliada en cobros
- CxP conciliada en pagos
- Cuenta de retención presente en línea de write-off
- Mayor general y balance no alterados en estructura base

---

## Impacto fiscal

### Campos de trazabilidad

| Campo catálogo | Reporte DGII |
|----------------|--------------|
| `affects_606` | Compras con retenciones proveedor |
| `affects_607` | Ventas con retenciones cliente |

### Mapeo por retención

| Retención | 606 | 607 | Notas |
|-----------|-----|-----|-------|
| RET-GOB-5 | No | Sí | Retención ISR en ventas a gobierno |
| RET-ITBIS-30 | Sí | Sí | ITBIS retenido compras y cobros |
| RET-ITBIS-100 | Sí | Sí | ITBIS 100% |
| RET-INF-ISR-10 | Sí | No | ISR proveedor informal |
| RET-INF-ITBIS-75 | Sí | No | ITBIS informal 75% |
| RET-ISR-2 | Sí | Sí | ISR 2% N07-07 |
| RET-HON-10 | Sí | Sí | Honorarios / alquiler |

### Trazabilidad por factura

- NCF visible en línea del wizard (`justech_do_ncf`)
- Detalle de retenciones por factura antes de confirmar pago
- Monto retenido, base y porcentaje documentados en líneas transientes

### Reportes 606 / 607

Los wizards fiscales `justech.do.fiscal.report.wizard` siguen generando correctamente tras pagos con retención (validación de regresión incluida).

---

## Reglas de negocio

1. **No se inventan tasas** — impuestos `l10n_do` vinculados al catálogo; porcentaje nominal documentado en catálogo.
2. **ITBIS 30/100/75%** — `ITBIS facturado × tasa nominal` (Fase 18.4).
3. **ISR 5/10/2%** — `base imponible × tasa nominal`.
4. Retención desactivada **no aparece** en selector ni afecta pagos.
5. Total retenido no puede superar monto a aplicar.

### Ejemplo corregido (Fase 18.4)

Factura RD$10,000 + ITBIS RD$1,800:

| Retención | Cálculo | Monto |
|-----------|---------|-------|
| ITBIS 100% | 1,800 × 100% | RD$1,800 |
| ITBIS 30% | 1,800 × 30% | RD$540 |
| ISR 2% | 10,000 × 2% | RD$200 |

---

## Listo para producción

**No.** Fase 18.4 corrige cálculo ITBIS en TEST. Requiere:

1. PASS completo en `hellenia_test` (cálculo 18.4 validado 2026-07-01)
2. Aprobación explícita del usuario
3. Backup PROD antes de promoción
4. `-u hellenia_account` + `docker compose restart odoo` en TEST/PROD
