# Configuración Contable — Hellenia

**Fase:** 8  
**Ambiente:** DEV  
**Fecha:** 2026-06-30  
**Estado bloque:** **PASS CON OBSERVACIONES**

---

## 1. Plan contable

| Parámetro | Valor |
|-----------|-------|
| Plantilla | `do` (República Dominicana) |
| Cuentas | 289 |
| Origen | `l10n_do` — TC-002 |
| Moneda funcional | DOP |

**Validación contador oficial (Glys Nuñez):** Pendiente firma sobre cuentas automáticas por categoría.

---

## 2. Diarios

| Código | Tipo | Rol |
|--------|------|-----|
| INV | sale | Facturación clientes + NCF |
| FACTU | purchase | Facturas proveedores + NCF |
| BNK1 | bank | Movimientos bancarios López de Haro |
| CSH1 | cash | Efectivo (Fase 3.5) |
| MISCE | general | Asientos varios |
| CABA | general | Criterio de caja impuestos |
| CAMBI | general | Diferencias cambio USD/DOP |
| TAX | general | Declaraciones fiscales |
| STJ | general | Valoración inventario |
| PCC | sale | Punto de cobro (EE) |

**Total:** 10 diarios

---

## 3. Impuestos

| Categoría | Cantidad |
|-----------|----------|
| Total impuestos | 37 |
| ITBIS (variantes) | 14 |
| Posiciones fiscales | 11 |

### ITBIS principal

| Impuesto | Tasa | Uso |
|----------|------|-----|
| 18% ITBIS | 18% | Ventas/compras estándar |
| ITBIS Exempt | 0% | Exentos |
| Variantes compra | 16%, 9%, 8%, retenciones | Según posición fiscal |

Fuente: `config/company/taxes.yaml` — no modificar vía custom.

---

## 4. Posiciones fiscales

11 posiciones estándar `l10n_do`:

- DO Domestic
- Governmental
- Informal Supplier of Goods
- Non-Profit Services
- Outside Services
- P. Legal Services / P. Physical Services
- Restaurants, Special Regimes, To Take Away
- P. Legal Surveillance

---

## 5. Métodos de pago

| Método | Diario | Dirección |
|--------|--------|-----------|
| Efectivo | CSH1 | Entrada / Salida |
| Transferencia | BNK1 | Entrada / Salida |
| Tarjetas | BNK1 | Entrada (manual) |
| Link de pago | BNK1 | Entrada (estructura) |
| Cheques | BNK1 | Salida |

---

## 6. Bancos

| Banco | Cuenta | Moneda |
|-------|--------|--------|
| Banco López de Haro | 4040043811 | DOP |
| Banco López de Haro | 4010461048 | USD |

Conciliación bancaria: módulo EE `account_accountant` — disponible, no parametrizada en detalle.

---

## 7. Cuentas automáticas

| Área | Estado |
|------|--------|
| Cuentas por cobrar | Estándar plan `do` |
| Cuentas por pagar | Estándar plan `do` |
| Ingresos / gastos | Por categoría producto — pendiente validación |
| Diferencias cambio | Diario CAMBI |

---

## 8. Secuencias

Secuencias estándar Odoo por diario. NCF gestionado por módulo Justech (ver localización RD).

---

## 9. Asientos automáticos

| Origen | Estado |
|--------|--------|
| Factura cliente | ✅ Validado Fase 4/6 |
| Factura proveedor | ✅ Validado |
| Pagos | Estándar |
| Valoración inventario | Parcial — ver nota Fase 4 |
| Cierre período | Pendiente UAT contabilidad |

---

## 10. Validación

| Check | Resultado |
|-------|-----------|
| Diarios ≥ 8 | ✅ (10) |
| Impuestos ≥ 14 | ✅ (37) |
| Cuentas ≥ 200 | ✅ (289) |
| Posiciones fiscales | ✅ (11) |
| Métodos pago | ✅ |

```
Estado: PASS CON OBSERVACIONES
Causa: validación contador pendiente
Impacto: operación UAT posible; firma contable requerida pre Go-Live
Prioridad: P1 validación Glys Nuñez
Propuesta: checklist cuentas automáticas por categoría inventario oficial
```

---

## 11. Referencias

- `config/company/journals.yaml`
- `config/company/taxes.yaml`
- `config/company/banks.yaml`
- [DOMINICAN_ACCOUNTING_CERTIFICATION.md](DOMINICAN_ACCOUNTING_CERTIFICATION.md)
