# Fase 19 — Validación 606 TEST

## Casos de prueba

### Unit tests Odoo (`custom/justech_l10n_do_reports/tests/test_phase19_dgii_606.py`)

| Caso | Descripción |
|------|-------------|
| `test_partner_id_type_from_vat` | RNC 9 dígitos → tipo 1; Cédula 11 → tipo 2 |
| `test_p0_fields_on_move` | NCF y estatus DGII en factura compra |
| `test_validate_606_missing_ncf` | Validación detecta factura sin NCF |
| `test_export_606_xlsx` | Genera Excel y guarda en historial |
| `test_withholding_catalog_dgii_code` | RET-HON-10 tiene código `02` |
| `test_credit_note_ncf_modified` | NC proveedor referencia NCF original |

### Script TEST VPS (`scripts/phase19-validate-606-test.py`)

Ejecutar:

```bash
bash scripts/run-phase19-test.sh
```

Evidencia: `evidence/phase19-606-test.json`

Casos:

1. `partner_id_type_b11` — proveedor formal RNC
2. `partner_id_type_b13` — proveedor informal cédula
3. `invoice_posted` — factura compra publicada
4. `invoice_ncf` — NCF asignado
5. `dgii_line_status` — estatus válido
6. `validate_606` — sin errores de validación
7. `export_606_xlsx` — archivo generado
8. `dgii_withholding_code` — catálogo con código DGII

### Datos demo recomendados en TEST

| Escenario | Partner | NCF | Notas |
|-----------|---------|-----|-------|
| Proveedor formal B11 | RNC 9 dígitos | B11... | Compra con ITBIS 18% |
| Proveedor informal B13 | Cédula 11 dígitos | B13... | Gastos menores |
| Compra exenta | Formal | B11... | Sin impuesto ITBIS |
| Retención ITBIS 30% | Formal | B11... | Catálogo RET-ITBIS-30 |
| Retención ISR 10% | Informal | B13... | Catálogo RET-INF-ISR-10 |
| NC proveedor | Formal | B04... | `ncf_modified` = NCF original |
| Pago parcial/total | Formal | B11... | Forma pago col Z |

## Criterios PASS

- Todos los unit tests Odoo pasan
- Script TEST: `pass: true` (8/8)
- Excel abre en LibreOffice/Excel
- Columnas A–AA presentes en fila 11
- Montos coinciden con facturas de prueba ±0.01

## Ejecución local DEV

```bash
docker compose -f docker/dev/docker-compose.yml run --rm odoo \
  odoo -d hellenia_dev --test-enable \
  --test-tags=/justech_l10n_do_reports \
  --stop-after-init
```

## Resultado

| Entorno | Estado | Notas |
|---------|--------|-------|
| DEV | Pendiente ejecución en VPS/imagen | Código listo |
| TEST | Pendiente deploy rama + `run-phase19-test.sh` | Sin tocar PROD |

Actualizar esta tabla tras ejecutar en cada entorno.
