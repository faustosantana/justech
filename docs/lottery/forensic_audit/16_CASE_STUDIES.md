# 16 — Estudios de caso

Casos educativos mezclando hits, compañeros, vecinos y sin relación.

## FX-001 — 2019-07-27 · fuerte **11**


```
Motor
 └─ 11
     ├─ generador: 35 (Quiniela Leidsa)
     ├─ confirmadores: [91] (['Quiniela Real'])
     ├─ compañeros T1: [6, 43, 54, 86]
     ├─ vecinos T2: [57, 69, 91]
     └─ ventana D+1…D+7
         └─ bucket: FUERTE_EXACTO
             más cercano: 11 (dist 0)
```

- ¿Salió el fuerte?: **Sí**
- Primer día (si aplica): 1
- Primera aparición: {'date': '2019-07-28', 'lottery': 'New York 2:30', 'position': 1, 'source_reference': '47626'}
- Conteos por distancia: {'SIN_RELACION': 120, 'RELACION_INDIRECTA': 12, 'FUERTE_EXACTO': 4, 'VECINO_TABLA2': 5, 'COMPANERO_TABLA1': 4}

## FX-002 — 2019-08-01 · fuerte **71**


```
Motor
 └─ 71
     ├─ generador: 42 (New York 10:30)
     ├─ confirmadores: [89] (['Quiniela Leidsa'])
     ├─ compañeros T1: [7, 18, 23, 50, 55, 66]
     ├─ vecinos T2: [12, 41, 56, 89]
     └─ ventana D+1…D+7
         └─ bucket: FUERTE_EXACTO
             más cercano: 71 (dist 0)
```

- ¿Salió el fuerte?: **Sí**
- Primer día (si aplica): 1
- Primera aparición: {'date': '2019-08-02', 'lottery': 'Gana Mas', 'position': 2, 'source_reference': '163137'}
- Conteos por distancia: {'SIN_RELACION': 83, 'FUERTE_EXACTO': 3, 'RELACION_INDIRECTA': 50, 'COMPANERO_TABLA1': 6, 'VECINO_TABLA2': 3}

## FX-003 — 2019-07-24 · fuerte **50**


```
Motor
 └─ 50
     ├─ generador: 42 (Quiniela Leidsa)
     ├─ confirmadores: [5] (['Gana Mas'])
     ├─ compañeros T1: [7, 18, 23, 55, 66, 71]
     ├─ vecinos T2: [5]
     └─ ventana D+1…D+7
         └─ bucket: FUERTE_EXACTO
             más cercano: 50 (dist 0)
```

- ¿Salió el fuerte?: **Sí**
- Primer día (si aplica): 5
- Primera aparición: {'date': '2019-07-29', 'lottery': 'New York 2:30', 'position': 1, 'source_reference': '47625'}
- Conteos por distancia: {'RELACION_INDIRECTA': 26, 'SIN_RELACION': 106, 'COMPANERO_TABLA1': 13, 'FUERTE_EXACTO': 1}

## FX-004 — 2019-07-27 · fuerte **86**


```
Motor
 └─ 86
     ├─ generador: 35 (Quiniela Leidsa)
     ├─ confirmadores: [46] (['New York 10:30'])
     ├─ compañeros T1: [6, 11, 43, 54]
     ├─ vecinos T2: [19, 46]
     └─ ventana D+1…D+7
         └─ bucket: COMPANERO_TABLA1
             más cercano: 11 (dist 1)
```

- ¿Salió el fuerte?: **No**
- Primer día (si aplica): None
- Primera aparición: None
- Conteos por distancia: {'SIN_RELACION': 115, 'COMPANERO_TABLA1': 8, 'RELACION_INDIRECTA': 20, 'VECINO_TABLA2': 2}

### Banderas sobre el ejemplo más cercano (miss)

| Pregunta | Respuesta |
|----------|----------|
| ¿Grupo T1? | True |
| ¿Grupo T2? | False |
| ¿Código T1? | True |
| ¿Código T2? | False |
| ¿Compañero? | True |
| ¿Vecino? | False |
| ¿Indirecta? | False |
| Distancia | 1 (COMPANERO_TABLA1) |

## FX-005 — 2019-07-29 · fuerte **5**


```
Motor
 └─ 5
     ├─ generador: 37 (Quiniela Loteka,Quiniela Real)
     ├─ confirmadores: [50] (['New York 2:30'])
     ├─ compañeros T1: [10, 42]
     ├─ vecinos T2: [50]
     └─ ventana D+1…D+7
         └─ bucket: COMPANERO_TABLA1
             más cercano: 10 (dist 1)
```

- ¿Salió el fuerte?: **No**
- Primer día (si aplica): None
- Primera aparición: None
- Conteos por distancia: {'SIN_RELACION': 119, 'RELACION_INDIRECTA': 21, 'COMPANERO_TABLA1': 4, 'VECINO_TABLA2': 1}

### Banderas sobre el ejemplo más cercano (miss)

| Pregunta | Respuesta |
|----------|----------|
| ¿Grupo T1? | True |
| ¿Grupo T2? | False |
| ¿Código T1? | True |
| ¿Código T2? | False |
| ¿Compañero? | True |
| ¿Vecino? | False |
| ¿Indirecta? | False |
| Distancia | 1 (COMPANERO_TABLA1) |

## FX-006 — 2019-08-02 · fuerte **26**


```
Motor
 └─ 26
     ├─ generador: 28 (Loteria Nacional)
     ├─ confirmadores: [34] (['New York 2:30'])
     ├─ compañeros T1: [21, 53]
     ├─ vecinos T2: [34, 59, 72]
     └─ ventana D+1…D+7
         └─ bucket: COMPANERO_TABLA1
             más cercano: 21 (dist 1)
```

- ¿Salió el fuerte?: **No**
- Primer día (si aplica): None
- Primera aparición: None
- Conteos por distancia: {'RELACION_INDIRECTA': 36, 'SIN_RELACION': 103, 'COMPANERO_TABLA1': 3, 'VECINO_TABLA2': 4}

### Banderas sobre el ejemplo más cercano (miss)

| Pregunta | Respuesta |
|----------|----------|
| ¿Grupo T1? | True |
| ¿Grupo T2? | False |
| ¿Código T1? | True |
| ¿Código T2? | False |
| ¿Compañero? | True |
| ¿Vecino? | False |
| ¿Indirecta? | False |
| Distancia | 1 (COMPANERO_TABLA1) |

## FX-007 — 2019-10-21 · fuerte **45**


```
Motor
 └─ 45
     ├─ generador: 50 (Gana Mas)
     ├─ confirmadores: [32] (['New York 10:30'])
     ├─ compañeros T1: []
     ├─ vecinos T2: [32]
     └─ ventana D+1…D+7
         └─ bucket: VECINO_TABLA2
             más cercano: 32 (dist 3)
```

- ¿Salió el fuerte?: **No**
- Primer día (si aplica): None
- Primera aparición: None
- Conteos por distancia: {'SIN_RELACION': 139, 'VECINO_TABLA2': 3, 'RELACION_INDIRECTA': 4}

### Banderas sobre el ejemplo más cercano (miss)

| Pregunta | Respuesta |
|----------|----------|
| ¿Grupo T1? | False |
| ¿Grupo T2? | True |
| ¿Código T1? | False |
| ¿Código T2? | True |
| ¿Compañero? | False |
| ¿Vecino? | True |
| ¿Indirecta? | False |
| Distancia | 3 (VECINO_TABLA2) |

## FX-008 — 2019-11-27 · fuerte **89**


```
Motor
 └─ 89
     ├─ generador: 48 (New York 10:30)
     ├─ confirmadores: [41] (['New York 2:30'])
     ├─ compañeros T1: [73]
     ├─ vecinos T2: [12, 41, 56, 71]
     └─ ventana D+1…D+7
         └─ bucket: VECINO_TABLA2
             más cercano: 12 (dist 3)
```

- ¿Salió el fuerte?: **No**
- Primer día (si aplica): None
- Primera aparición: None
- Conteos por distancia: {'SIN_RELACION': 93, 'RELACION_INDIRECTA': 43, 'VECINO_TABLA2': 8}

### Banderas sobre el ejemplo más cercano (miss)

| Pregunta | Respuesta |
|----------|----------|
| ¿Grupo T1? | False |
| ¿Grupo T2? | True |
| ¿Código T1? | False |
| ¿Código T2? | True |
| ¿Compañero? | False |
| ¿Vecino? | True |
| ¿Indirecta? | False |
| Distancia | 3 (VECINO_TABLA2) |

## FX-009 — 2022-03-22 · fuerte **96**


```
Motor
 └─ 96
     ├─ generador: 54 (New York 10:30)
     ├─ confirmadores: [15] (['Loteria Nacional'])
     ├─ compañeros T1: []
     ├─ vecinos T2: [15]
     └─ ventana D+1…D+7
         └─ bucket: SIN_RELACION
             más cercano: None (dist 5)
```

- ¿Salió el fuerte?: **No**
- Primer día (si aplica): None
- Primera aparición: None
- Conteos por distancia: {'SIN_RELACION': 145}

### Banderas sobre el ejemplo más cercano (miss)

| Pregunta | Respuesta |
|----------|----------|
| ¿Grupo T1? | False |
| ¿Grupo T2? | False |
| ¿Código T1? | False |
| ¿Código T2? | False |
| ¿Compañero? | False |
| ¿Vecino? | False |
| ¿Indirecta? | False |
| Distancia | 5 (SIN_RELACION) |

## FX-010 — 2019-07-24 · fuerte **7**


```
Motor
 └─ 7
     ├─ generador: 42 (Quiniela Leidsa)
     ├─ confirmadores: [9, 70] (['Loteria Nacional', 'New York 10:30', 'New York 2:30'])
     ├─ compañeros T1: [18, 23, 50, 55, 66, 71]
     ├─ vecinos T2: [9, 22, 29, 35, 42, 44, 53, 63, 70, 90]
     └─ ventana D+1…D+7
         └─ bucket: FUERTE_EXACTO
             más cercano: 7 (dist 0)
```

- ¿Salió el fuerte?: **Sí**
- Primer día (si aplica): 2
- Primera aparición: {'date': '2019-07-26', 'lottery': 'Quiniela Leidsa', 'position': 1, 'source_reference': '116735'}
- Conteos por distancia: {'RELACION_INDIRECTA': 58, 'SIN_RELACION': 67, 'VECINO_TABLA2': 7, 'COMPANERO_TABLA1': 12, 'FUERTE_EXACTO': 2}

## FX-011 — 2019-08-06 · fuerte **72**


```
Motor
 └─ 72
     ├─ generador: 40 (Quiniela Real)
     ├─ confirmadores: [34, 59] (['New York 2:30', 'Quiniela Leidsa'])
     ├─ compañeros T1: [8, 19, 51, 56, 67]
     ├─ vecinos T2: [26, 34, 59]
     └─ ventana D+1…D+7
         └─ bucket: FUERTE_EXACTO
             más cercano: 72 (dist 0)
```

- ¿Salió el fuerte?: **Sí**
- Primer día (si aplica): 1
- Primera aparición: {'date': '2019-08-07', 'lottery': 'Gana Mas', 'position': 3, 'source_reference': '163132'}
- Conteos por distancia: {'SIN_RELACION': 110, 'FUERTE_EXACTO': 2, 'RELACION_INDIRECTA': 27, 'COMPANERO_TABLA1': 7}
