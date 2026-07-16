# FASE 2 — Causa raíz (DEV) — Estado y alertas rangos NCF

Fecha: 2026-07-16  
Entorno: `erp.justech.do` / BD `justech_dev` / host `207.244.242.58`  
Backup: `/opt/odoo-dev/backups/ncf-range-alerts-dev-20260716_205552`  
Restore test: PASS (moves=2410, ranges=14)

## Modelo

| Ítem | Valor |
|---|---|
| Modelo | `justech.do.ncf.range` |
| Tabla | `justech_do_ncf_range` |
| Empresa | `company_id` (Many2one `res.company`, required, index) |
| Tipo doc | `document_type_id` → `justech.do.fiscal.document.type` |
| Estado | `state` Selection: draft / active / depleted / expired / cancelled |
| Disponibles | `remaining_count` (computed, **no stored**) |
| % Consumido | `pct_used` (computed, **no stored**) |
| Archivo | `custom/justech_l10n_do_ncf/models/ncf_range.py` |

## INCIDENTE 1 — Causa exacta

Tras marcar `state='depleted'`, los computes **ignoran** la matemática real y fuerzan UI:

```python
# _compute_remaining
if rec.state in ("depleted", "cancelled"):
    rec.remaining_count = 0   # ← fuerza 0 aunque sequence_end se amplíe

# _compute_pct_used
if rec.state in ("depleted", "cancelled"):
    rec.pct_used = 100.0      # ← fuerza 100%
```

Además:

- **No existe** `write()`/`onchange` que recalcule `state` al editar `sequence_end`.
- `consume_next` sí actualiza state a `depleted`/`active`, pero **ampliar el final no llama** a esa lógica.
- Resultado: rango ampliado permanece `depleted` → UI muestra Agotado / 0 / 100%.

## INCIDENTE 2 — Causa exacta

- Existe solo `company.justech_do_ncf_alert_days` (días a vencimiento) y `ncf_range_audit_service` (lectura/diagnóstico).
- **No hay** cron de alertas de umbral/agotado.
- **No hay** creación de `mail.activity` ni plantilla de correo por rango.
- **No hay** umbrales preventivo/crítico configurables.
- Cron existente `FISCAL SEQUENCE: Expire sequences` es de secuencia fiscal Adel/legado, no del motor Justech de alertas.

## Multiempresa (auditoría)

- `_find_active_range` / `_find_active_range_for_update` filtran `company_id = company.id` → OK.
- `consume_next` valida `move.company_id == range.company_id` → OK.
- `normalize_range_names` usa `sudo()` + search por prefix **sin** filtro company (solo renombra `name`; riesgo bajo pero a endurecer).
- Record rules: revisar `justech_l10n_do_ncf_rules.xml` (company).

## Qué NO está roto

- Campos `sequence_start` / `sequence_end` / `next_sequence` se persisten correctamente.
- El cálculo matemático `final - proxima + 1` es correcto **si** state ≠ depleted/cancelled.
- Fingerprints DEV pre-cambio: `ranges_fp=fda13bf0…` `seq_fp=ec58c27e…` `gl_diff=0`.

## Corrección autorizada (siguiente)

1. Fórmula única de disponibles/% sin depender del estado para ocultar números.
2. Recálculo de estado con prioridad Cerrado > Vencido > Agotado > Activo > Borrador al ampliar/editar.
3. Alertas `mail.activity` (+ mail) por compañía, idempotentes, sin cruce multiempresa.
4. UAT SAVEPOINT en las 4 empresas; 0 NCF consumidos reales.
