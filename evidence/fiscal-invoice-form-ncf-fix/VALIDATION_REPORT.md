# Fix: display fiscal seguro en formularios (regresión FP/2026/03/0001)

**Entorno:** erp.justech.do / justech_dev  
**Módulo:** justech_l10n_do_ncf 19.0.2.2.3  
**Commit:** pendiente

## Causa

1. Deploy incorrecto temporal: archivos nuevos quedaron en la raíz del módulo (no en `models/` / `views/`), por lo que el servidor seguía con campos viejos / vista inconsistente tras `-u`.
2. Campo almacenado `justech_do_dgii_fiscal_state=incomplete` en histórico Adel (default) — no debe mostrarse como “Estado fiscal” de UI.
3. Tras reinicios, errores de websocket en log (bus 8072); no hubo traceback de compute sobre move 1367.

## Corrección

Campos UI-only vía Fiscal Data Provider:

- `fiscal_document_type_display`
- `fiscal_ncf_display`
- `fiscal_status_display`

Reglas: sin escritura, sin backfill; histórico Adel con NCF → **Histórico compatible** (nunca “Incompleto”); Justech → **Válido**. Compute endurecido con try/except. Pestaña compacta.

## Validación

Browser 6/6 + 4 empresas: PASS (`validation.json`).  
FP/2026/03/0001 carga completa, NCF B0100008679, estado Histórico compatible.  
Pagos: 738 (intactos).
