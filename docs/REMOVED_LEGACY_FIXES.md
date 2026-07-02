# Código legacy eliminado — Fases 19.x (Fase 20.1)

## Eliminado de `payment_partner_wizard.py`

| Artefacto | Fase origen | Motivo eliminación |
|-----------|-------------|-------------------|
| `create()` → `_load_pending_invoices()` | 19.6+ | Destruía estado UI en web_save |
| `_enforce_server_selection_guard()` | 19.9 | Parche sobre arquitectura rota |
| `_selected_line_ids_sql()` | 19.9 | Parche SQL innecesario con arquitectura correcta |
| `_log_selection_debug()` | 19.9 | Logging temporal forense |
| `_selected_lines()` con guards | 19.6–19.9 | Reemplazado por `_validate_lines_for_register()` |
| `_effective_amount_to_pay()` | 19.3 | Lógica absorbida en validación + `line.amount_to_pay` |
| `line.write()` que limpiaba montos | 19.9 | Sustituido por validación explícita al registrar |
| `amount_to_pay = abs(residual)` en carga | pre-19.9 | Causa raíz UI |
| Logging `HELLENIA_FORENSIC` | 20.0 | Solo investigación |
| Archivo `payment_partner_wizard_prod_v23.py` | 20.0 | Copia forense temporal |

## Conservado (flujo Enterprise válido)

- Integración `account.payment.register` con `force_payment_move` para parciales
- Retenciones por línea (`_recompute_line_withholdings`, `_withholding_commands_for_line`)
- Vista con `force_save` en `apply` y `amount_to_pay`
- Onchange `apply` que sugiere residual **solo** al marcar factura

## PASS invalidados

Todos los PASS de fases 19.3, 19.4, 19.6, 19.7, 19.9, 19.11 quedan invalidados (pruebas shell/ORM, no UI real).
