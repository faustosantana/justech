# Matriz final Compras — auditoría lectura
## Confirmaciones
- Catálogo LATAM recibido: B01–B04, B14–B16, E31–E34, E41, E43–E47 — **todos activos**.
- Ningún tipo recibido consume secuencia propia (NCF manual del proveedor).
- Catálogo emitidos Compras (Justech purchase): **solo B11, B13, B17** (normativa DGII + PURCHASE_NCF_PREFIXES).
- Justech **no** tiene tipos E en catálogo de emisión (correcto para no emitir e-CF desde Compras).
- Alineación normativa DGII: ✅ | Alineación histórico ERP (recibidos latam; emisión B11/B13/B17): ✅
- Producción **no modificada**.

## Emitidos por empresa (detalle crítico)

| Empresa | Tipo | Doc | Motor | Consume seq | Rango | Próximo NCF | Estado |
|---|---|---|---|---|---|---|---|
| JUSTECH S.R.L. | B11 | emitido | Justech | Sí | 11-15 (active) | B1100000011 | Correcto |
| JUSTECH S.R.L. | B13 | emitido | Justech | Sí | 213-217 (active) | B1300000213 | Correcto |
| JUSTECH S.R.L. | B17 | emitido | Justech | Sí | — | — | Falta rango |
| Omni Solutions SRL | B11 | emitido | Justech | Sí | — | — | Falta rango |
| Omni Solutions SRL | B13 | emitido | Justech | Sí | — | — | Falta rango |
| Omni Solutions SRL | B17 | emitido | Justech | Sí | — | — | Falta rango |
| Just Office SRL | B11 | emitido | Justech | Sí | — | — | Falta rango |
| Just Office SRL | B13 | emitido | Justech | Sí | — | — | Falta rango |
| Just Office SRL | B17 | emitido | Justech | Sí | — | — | Falta rango |
| PlugSafe SRL | B11 | emitido | Justech | Sí | — | — | Falta rango |
| PlugSafe SRL | B13 | emitido | Justech | Sí | — | — | Falta rango |
| PlugSafe SRL | B17 | emitido | Justech | Sí | — | — | Falta rango |

## Recibidos (todas las empresas — idéntico)

Para JUSTECH, Omni Solutions, Just Office y PlugSafe (MF Plug & Safe):

| Tipo | Doc | Motor | Consume seq | Rango | Próximo | Estado |
|---|---|---|---|---|---|---|
| B01 | recibido | LATAM | No | N/A | N/A | Correcto |
| B02 | recibido | LATAM | No | N/A | N/A | Correcto |
| B03 | recibido | LATAM | No | N/A | N/A | Correcto |
| B04 | recibido | LATAM | No | N/A | N/A | Correcto |
| B14 | recibido | LATAM | No | N/A | N/A | Correcto |
| B15 | recibido | LATAM | No | N/A | N/A | Correcto |
| B16 | recibido | LATAM | No | N/A | N/A | Correcto |
| E31 | recibido | LATAM | No | N/A | N/A | Correcto |
| E32 | recibido | LATAM | No | N/A | N/A | Correcto |
| E33 | recibido | LATAM | No | N/A | N/A | Correcto |
| E34 | recibido | LATAM | No | N/A | N/A | Correcto |
| E41 | recibido | LATAM | No | N/A | N/A | Correcto |
| E43 | recibido | LATAM | No | N/A | N/A | Correcto |
| E44 | recibido | LATAM | No | N/A | N/A | Correcto |
| E45 | recibido | LATAM | No | N/A | N/A | Correcto |
| E46 | recibido | LATAM | No | N/A | N/A | Correcto |
| E47 | recibido | LATAM | No | N/A | N/A | Correcto |

CSV completo: `FINAL_MATRIX_BY_COMPANY.csv` (80 filas).
