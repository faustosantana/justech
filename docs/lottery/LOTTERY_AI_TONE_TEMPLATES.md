# Lottery IA — Tone Templates

Plantillas en `backend/app/lottery/ai/tone_templates.py`.

| Key | Uso |
|-----|-----|
| conservador | breve, cauteloso |
| conversacional | natural, seguimiento útil |
| analitico | métricas, tablas, parámetros |
| ejecutivo | resumen + KPIs |
| profundo | multi-tool / cobertura |
| estricto | dominio estricto, mínima expansión |

Cada plantilla define: `tone`, `verbosity`, `analysis_depth`, `max_insights`,
`tables_enabled`, `parameters_visible`, `suggestions_enabled`, `clarification_style`,
`disclaimer_mode`, `max_response_length`, `system_addon`.

## Seguridad inmutable

`CRITICAL_SAFETY_KEYS` se eliminan de cualquier override de payload.
Las plantillas **no pueden** desactivar dominio estricto, no-predicción, ni aislamiento tenant.

## Preferencias

- Tenant default + user override (`lottery_ai_tone_preferences`)
- Tenant puede bloquear override (`allow_user_override=false`)
- Reset API: `POST /tones/preference/reset`
- Preview lado a lado v2/v3: `POST /tones/preview` (no muta config activa)
