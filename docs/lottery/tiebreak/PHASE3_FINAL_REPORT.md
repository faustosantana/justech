# PHASE 3 — Informe final

## Objetivo cumplido

Motor de desempate multi-fuerte + validación prospectiva, sin tocar Producción ni fórmulas T1/T2.

## Hallazgo central

Los 14 errores Fase 2 son **fallos de ranking en empate**, no de descubrimiento.  
Regla operativa: `TIEBREAK_PROFILE_SOCIO_V1` + `EMPATE_MULTI_FUERTE` (umbral práctico 0.0).

Selección validation (single, sin multi): `TIEBREAK_SOURCE_ORDER` (top-1 97%).  
Operativa honesta: socio + multi-fuerte.

## Números (lab, limit 200; test bloqueado hasta selección)

| Métrica | Valor |
|---------|------:|
| Val baseline top-1 | 95.5% |
| Val selected (SOURCE_ORDER) top-1 | 97.0% |
| Val socio+multi top-1 estricto | 94.0% |
| Val socio+multi top-1∨multi | **100%** |
| Val socio+multi top-2 | 100% |
| Test baseline top-1 | 92.5% |
| Test selected single top-1 | 93.0% |
| Test socio+multi top-1∨multi | **98.5%** |
| Test multi-fuerte rate | 13% |
| 14 errores baseline top-1 | 0/14 |
| 14 socio+multi top-1 único | 4/14 |
| 14 socio+multi top-1∨multi | 13/14 |
| 14 multi-fuerte rate | ~71% |

## Entregables

### Código

- `analysis_engine/tiebreak_engine.py`
- `analysis_engine/tiebreak_lab.py`
- `analysis_engine/prospective_validation.py`
- Integración en `complete_analysis_service.py`
- API: `/tiebreak/*`, `/prospective-validation/*`
- UI: `/lottery/tiebreak-validation`
- J-11A: intents de desempate / 14 errores / predicciones bloqueadas (solo evidencia)

### Docs

Este directorio (`docs/lottery/tiebreak/`).

### Artefactos

`artifacts/tiebreak/*`

### Pruebas

`backend/tests/lottery/tiebreak/test_tiebreak_phase3.py`

## Criterios de aceptación

1. 14 errores auditados — sí  
2. Matriz de diferencias — sí  
3. Hipótesis sin usar test para elegir — sí  
4. Regla seleccionada documentada — sí  
5. Histórico sigue en candidatos / top-2 — sí  
6. Top-1 sin deterioro material en casos correctos — sí (M1–M5 preservados)  
7. Multi-fuerte cuando no resoluble — sí  
8. Decisiones trazables — sí  
9. Validación prospectiva bloqueable — sí  
10. Pruebas — ver corrida en entrega  
11. Producción intacta — sí (`production_modified: false`)

## GO / NO-GO

**GO condicional a piloto DEV/UAT** — no Producción.  
Usar multi-fuerte en UI; no apostar; trust en top-2 / peers empatados.

## Limitaciones

- Históricos D+1/D+3 en evidencia aún no aportan separación fuerte en estos 14.
- Store prospectivo en memoria (DEV).
- Top-1 en multi-fuerte no se contabiliza como acierto único (intencional).
