# Fase 19.2 — Limpieza data UAT/demo en TEST

## Objetivo

Excluir fiscalmente la data histórica de pruebas sin borrar asientos contables.

## Script

```bash
bash scripts/run-phase19-2-test.sh
```

Paso 1 del orquestador: `scripts/phase19-2-exclude-uat-demo-test.py`

Evidencia: `evidence/phase19-2-cleanup.json`

## Criterios de exclusión

### Referencias que se excluyen

| Patrón ref | Origen |
|------------|--------|
| `UAT-*` | UAT Fase 9 |
| `PHASE4-*` | Fase 4 |
| `PHASE5-*` | Fase 5 |
| `PHASE19-*` | Script simple Fase 19 |
| `P19-ERR-*` | Casos de error 19.1 |

### Referencias que se mantienen incluidas

| Ref | Motivo |
|-----|--------|
| `P19-B11-ITBIS` | Demo certificación 19.1 |
| `P19-B11-EXEMPT` | Demo exenta |
| `P19-B11-WH-ITBIS30` | Demo retención ITBIS |
| `P19-B13-WH-ISR10` | Demo retención ISR |
| `P19-B13-MULTI-WH` | Demo multi-retención |
| `P19-B11-NC` | Demo nota crédito |

### Proveedores que se excluyen (por nombre)

- `UAT Proveedor Mobiliario RD`
- `Proveedor prueba Fase 4`
- `PHASE5 Proveedor Lab`
- `P19 Sin RNC` / `P19 Sin Tipo`
- Cualquier nombre con: UAT, Fase 4, Fase 5, PHASE4/5/19, Mobiliario RD, Proveedor prueba, Proveedor Lab

## Acción en cada factura excluida

```python
justech_do_include_in_dgii = False
justech_do_dgii_exclusion_reason = "Exclusión fiscal Fase 19.2 — data UAT/demo/prueba"
justech_do_dgii_fiscal_state = "excluded"
```

**No se cancelan, no se borran, no se toca PROD.**

## Reversión manual

Para re-incluir una factura:

1. Abrir factura proveedor en Odoo TEST
2. Marcar **Incluir en reportes DGII**
3. Limpiar motivo de exclusión
4. Validar período nuevamente

## Resultado esperado post-limpieza

- Facturas UAT/demo: estado `excluded`, fuera del 606
- Facturas P19 demo: estado `valid`, en el 606
- Período completo: `incomplete = 0` tras exclusión de data no reportable
