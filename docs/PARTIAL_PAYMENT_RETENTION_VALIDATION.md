# Validación abonos parciales con retención

## Regla

Cuando `monto_aplicado < residual`, la base se prorratea:

```
base_efectiva = base_completa × (monto_aplicado / residual)
retención = base_efectiva × (tasa / 100)
```

## Casos certificados (TEST)

| Caso | Factura | Abono | Retención | Resultado |
|------|---------|-------|-----------|-----------|
| Parcial sin WH | 11,800 | 5,000 | — | residual partial |
| Parcial ITBIS 100% | 11,800 | 5,000 | 762.71 | proporcional OK |
| Completo Gobierno 5% | 11,800 | 11,800 | 500.00 | OK |
| Multi 3 facturas | varias | varias | 0/540/1800 | OK |

## Conciliación

- CxC/CxP conciliado por monto bruto aplicado
- Banco recibe neto (aplicado − retenido)
- Estado factura: `partial` o `paid`
