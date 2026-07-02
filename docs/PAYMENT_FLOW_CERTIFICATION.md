# Certificación flujo de pagos — Fase 17

**Módulos:** `hellenia_account`, `hellenia_ux`

## Wizard de pago

| Columna | Estado |
|---------|--------|
| Factura | ✅ |
| NCF | ✅ |
| Fecha | ✅ |
| Vencimiento | ✅ |
| Moneda | ✅ |
| Total | ✅ |
| Pendiente | ✅ |
| Monto a aplicar | ✅ |

## Métodos

| Método | Diario auto | Campos extra |
|--------|-------------|--------------|
| Transferencia | BNKD/BNKU | Referencia |
| Efectivo | CSH1 | — |
| Tarjeta | BNKD/BNKU | Referencia, Autorización, Lote |
| Cheque | BNKD/BNKU | Banco, Número, Fecha |

## Regresión Fase 16

Ejecutada junto con Fase 17 — ver `evidence/phase17-payments-regression.json`
