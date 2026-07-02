# Fase 18 — Validación TEST

## Ejecución

```bash
bash scripts/run-phase18-test.sh
```

## Casos (15 + regresión)

| # | Caso |
|---|------|
| 01 | Pago sin retención |
| 02 | Una retención |
| 03 | Dos retenciones misma factura |
| 04 | Dos facturas retenciones distintas |
| 05 | Tres facturas mixtas |
| 06 | Pago parcial con retención |
| 07 | Pago total con retención |
| 08 | Pago proveedor con retención |
| 09 | Cobro cliente con retención |
| 10 | Reporte 606 |
| 11 | Reporte 607 |
| 12 | Asiento balanceado |
| 13 | Conciliación |
| 14 | PDF sin regresión |
| 15 | Wizard sin RPC error |

Regresión: Fase 17.4 wizard + Fase 16 pagos.

Evidencia: `evidence/phase18-withholding-test.json`

## Estado

**TEST: PASS 18/18** — regresión Fase 17.4: 18/18, Fase 16: 23/23

Evidencia: `evidence/phase18-withholding-test.json`

**PROD: NO promovido** — pendiente aprobación explícita.
