# 04 — Reproducción exacta

### M1

- Observados: [41, 41, 70]
- Manual: **29**
- Oficial: [29]
- Clase: `FUERTE_OFICIAL_UNICO` (ALTA)
- Evidencia: Motor produce únicamente 29.
### M2

- Observados: [41, 62]
- Manual: **75**
- Oficial: []
- Clase: `VECINO_T2_DIRECTO` (ALTA)
- Evidencia: 75 es vecino T2 de [62] sin ruta T1×T2 oficial.
### M3

- Observados: [49, 44, 70]
- Manual: **35**
- Oficial: [22, 35]
- Clase: `FUERTE_OFICIAL_ENTRE_VARIOS` (ALTA)
- Evidencia: Motor produce [22, 35]; socio eligió 35.
- Desempate: 35 tiene 2 confirmadores (44,70); 22 tiene 1 (70). Coincide con la elección manual en este caso. No se incorpora como regla; ver contraejemplos históricos.
- Comparación: `{'22': {'fuerte': 22, 'origin': 44, 'confirmers': [70], 'n_confirmers': 1, 't1_companions_of_origin': [22, 59, 70, 75, 91], 't2_group': [7, 9, 22, 29, 35, 42, 44, 53, 63, 70, 90], 't1_group': [22, 59, 70, 75, 91], 't1_pos': 1, 't2_pos': 3}, '35': {'fuerte': 35, 'origin': 49, 'confirmers': [44, 70], 'n_confirmers': 2, 't1_companions_of_origin': [35, 40, 83], 't2_group': [7, 9, 22, 29, 35, 42, 44, 53, 63, 70, 90], 't1_group': [35, 40, 83], 't1_pos': 1, 't2_pos': 5}}`
### M4

- Observados: [35, 14]
- Manual: **54**
- Oficial: [54]
- Clase: `FUERTE_OFICIAL_UNICO` (ALTA)
- Evidencia: Motor produce únicamente 54.
### M5

- Observados: [39, 58]
- Manual: **94**
- Oficial: [94]
- Clase: `FUERTE_OFICIAL_UNICO` (ALTA)
- Evidencia: 39+58→94 es fuerte oficial. 39+84→94 también. 58 y 84 son vecinos T2 del mismo grupo [58,84,94]; ambos son confirmadores válidos. No es necesario tratar 58 como error.
- Alterno 39+84: `{'pair': [39, 84], 'official': [94], 'detail': [{'fuerte': 94, 'origin': 39, 'confirmers': [84]}], '58_and_84_same_t2_group': True, 't2_group_58_84_94': [58, 84, 94], 'both_confirm_94': True}`


### M5b 39+84

- Oficial: [94]
- Clase: FUERTE_OFICIAL_UNICO

JSON: `manual_case_reproductions.json`
