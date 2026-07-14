# Tipos realmente emitidos desde Compras (histórico PRE Go-Live)

Fuente: `justech_pre_golive_ro` — universo completo `in_invoice|in_refund|in_receipt` = **782** (780 posted + 2 draft).

## Criterio de “emitido por la empresa”

Confirmado solo si:
1. NCF de serie de emisión en compras (B11/B13/B17 o E41/E43/E47), **y**
2. Linked a `account.fiscal.sequence` Adel del tipo compra correspondiente  
   **o** número dentro del rango AFS de compra de la compañía sin contradicción de serie.

No basta el tipo latam solo: B15 con NCF `E31…` = recibido mal tipificado.

## Resultado

| Prefijo | Docs | Estado | AFS | Clasificación |
|---|---|---|---|---|
| **B13** | 1 (`FP/2026/06/0001`, id 3140) | draft | Gasto Menor #8 → `B1300000213` | **EMITIDO DESDE COMPRAS** |
| B11 | 0 | — | rango Adel/Justech existe | **no utilizado** |
| B17 | 0 | — | sin rango | **no utilizado** |
| B14 | 0 NCF B14 en vendor | — | — | **no utilizado** |
| B15 | 2 posted tipo latam B15 | posted | no | **NO emitido** (NCF `E31…` = recibido) |
| B16 | 0 | — | — | **no utilizado** |
| B01/E31 posted | 778 | posted | no AFS | **RECIBIDOS** |
| E34 draft refund | 1 | draft | AFS “Nota de Crédito” (venta) | **NO emisión compra** (NCF proveedor E34) |

## Lista definitiva (únicos tipos emitidos realmente usados)

1. **B13 — Gastos Menores**

Ningún otro tipo aparece como comprobante emitido desde Compras en el histórico pre Go-Live.
