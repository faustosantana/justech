# 10+ casos históricos (muestra seed=20260726)


## HIST-001 — C1_manual_subset

**Fecha:** 2026-06-21  
**Veredicto:** FALLO  
**Fuerte oficial:** `29`  
**Único:** True  
**Manual (solo compare final):** 29  
**Look-ahead bloqueado:** True

### Observados
- Gana Mas | hora=None | pos=1 (1ro) | número=41 | draw_id=d6732010-5902-4533-a13c-2fb016cf6856 | source_ref=224681
- Quiniela Leidsa | hora=None | pos=1 (1ro) | número=70 | draw_id=a8a12588-b47e-4779-9ff5-67d54b8404c5 | source_ref=224686

### Fortalecidos oficiales
**Candidato 29**
- Generador (Tabla 1): 41 (Gana Mas)
- Compañeros T1 del generador: [13, 29, 93]
- Grupo T2 del candidato: [7, 9, 22, 29, 35, 42, 44, 53, 63, 70, 90]
- Confirmadores: [70] via ['Quiniela Leidsa']
- Nivel: 1 confirmación(es)
- Confirmador nunca fortalecido: True

### Señales T2 directas (rechazadas como fuerte)
```json
[
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 41,
    "lottery": "Gana Mas",
    "direct_t2_neighbor": 12,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 41,
    "lottery": "Gana Mas",
    "direct_t2_neighbor": 56,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 41,
    "lottery": "Gana Mas",
    "direct_t2_neighbor": 71,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 41,
    "lottery": "Gana Mas",
    "direct_t2_neighbor": 89,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 70,
    "lottery": "Quiniela Leidsa",
    "direct_t2_neighbor": 7,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 70,
    "lottery": "Quiniela Leidsa",
    "direct_t2_neighbor": 9,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 70,
    "lottery": "Quiniela Leidsa",
    "direct_t2_neighbor": 22,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 70,
    "lottery": "Quiniela Leidsa",
    "direct_t2_neighbor": 35,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  }
]
```

### Ventanas (independientes)
- Siguiente sorteo: No
- Mismo día (otros sorteos): No
- Día calendario siguiente: No
- Próximos 7 sorteos FEATURED: No

### Explicación
41 (Gana Mas) genera candidato T1 29; confirmado por [70] vía Tabla2 (Quiniela Leidsa). No apareció en ninguna ventana declarada. Veredicto: FALLO.

---

## HIST-002 — C3_manual_subset

**Fecha:** 2026-06-21  
**Veredicto:** FALLO  
**Fuerte oficial:** `[35, 22]`  
**Único:** False  
**Manual (solo compare final):** 35  
**Look-ahead bloqueado:** True

### Observados
- Quiniela Real | hora=None | pos=1 (1ro) | número=49 | draw_id=08526f84-7229-415a-822f-ddc032c5da71 | source_ref=224676
- Loteria Nacional | hora=None | pos=1 (1ro) | número=44 | draw_id=901c62d2-5868-4915-b6bd-3902516f518c | source_ref=224692
- Quiniela Leidsa | hora=None | pos=1 (1ro) | número=70 | draw_id=a8a12588-b47e-4779-9ff5-67d54b8404c5 | source_ref=224686

### Fortalecidos oficiales
**Candidato 35**
- Generador (Tabla 1): 49 (Quiniela Real)
- Compañeros T1 del generador: [35, 40, 83]
- Grupo T2 del candidato: [7, 9, 22, 29, 35, 42, 44, 53, 63, 70, 90]
- Confirmadores: [44, 70] via ['Loteria Nacional', 'Quiniela Leidsa']
- Nivel: 2 confirmación(es)
- Confirmador nunca fortalecido: True
**Candidato 22**
- Generador (Tabla 1): 44 (Loteria Nacional)
- Compañeros T1 del generador: [22, 59, 70, 75, 91]
- Grupo T2 del candidato: [7, 9, 22, 29, 35, 42, 44, 53, 63, 70, 90]
- Confirmadores: [70] via ['Quiniela Leidsa']
- Nivel: 1 confirmación(es)
- Confirmador nunca fortalecido: True

### Señales T2 directas (rechazadas como fuerte)
```json
[
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 44,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 7,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 44,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 9,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 44,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 29,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 44,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 42,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 44,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 53,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 44,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 63,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 44,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 70,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 44,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 90,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  }
]
```

### Ventanas (independientes)
- Siguiente sorteo: No
- Mismo día (otros sorteos): No
- Día calendario siguiente: No
- Próximos 7 sorteos FEATURED: No

### Explicación
49 (Quiniela Real) genera candidato T1 35; confirmado por [44, 70] vía Tabla2 (Loteria Nacional, Quiniela Leidsa). 44 (Loteria Nacional) genera candidato T1 22; confirmado por [70] vía Tabla2 (Quiniela Leidsa). No apareció en ninguna ventana declarada. Veredicto: FALLO.

---

## HIST-003 — C4_manual_subset

**Fecha:** 2026-06-23  
**Veredicto:** ACIERTO_EXACTO  
**Fuerte oficial:** `54`  
**Único:** True  
**Manual (solo compare final):** 54  
**Look-ahead bloqueado:** True

### Observados
- Loteria Nacional | hora=None | pos=1 (1ro) | número=35 | draw_id=1d1862a7-715a-4f63-9724-c77291187154 | source_ref=224790
- Quiniela Loteka | hora=None | pos=1 (1ro) | número=14 | draw_id=5faf3955-ba7a-4819-b7bc-00e0b4517b68 | source_ref=224784

### Fortalecidos oficiales
**Candidato 54**
- Generador (Tabla 1): 35 (Loteria Nacional)
- Compañeros T1 del generador: [6, 11, 43, 54, 86]
- Grupo T2 del candidato: [14, 54]
- Confirmadores: [14] via ['Quiniela Loteka']
- Nivel: 1 confirmación(es)
- Confirmador nunca fortalecido: True

### Señales T2 directas (rechazadas como fuerte)
```json
[
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 7,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 9,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 22,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 29,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 42,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 44,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 53,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 63,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  }
]
```

### Ventanas (independientes)
- Siguiente sorteo: No
- Mismo día (otros sorteos): No
- Día calendario siguiente: Sí — 2026-06-24 Quiniela Loteka pos 1 = 54 (ref 224826)
- Próximos 7 sorteos FEATURED: Sí — 2026-06-24 Quiniela Loteka pos 1 = 54 (ref 224826)

### Explicación
35 (Loteria Nacional) genera candidato T1 54; confirmado por [14] vía Tabla2 (Quiniela Loteka). Aparición posterior: 2026-06-24 Quiniela Loteka pos 1 = 54 (ref 224826). Veredicto: ACIERTO_EXACTO.

---

## HIST-004 — C5_manual_subset

**Fecha:** 2026-07-22  
**Veredicto:** ACIERTO_EXACTO  
**Fuerte oficial:** `54`  
**Único:** True  
**Manual (solo compare final):** 54  
**Look-ahead bloqueado:** True

### Observados
- New York 2:30 | hora=None | pos=1 (1ro) | número=35 | draw_id=69f3cf8d-490a-4be2-ac7e-67ec4dc148c5 | source_ref=226039
- Loteria Nacional | hora=None | pos=1 (1ro) | número=14 | draw_id=3aa518e2-a381-45b7-8c5e-7e19825dc8d5 | source_ref=226060

### Fortalecidos oficiales
**Candidato 54**
- Generador (Tabla 1): 35 (New York 2:30)
- Compañeros T1 del generador: [6, 11, 43, 54, 86]
- Grupo T2 del candidato: [14, 54]
- Confirmadores: [14] via ['Loteria Nacional']
- Nivel: 1 confirmación(es)
- Confirmador nunca fortalecido: True

### Señales T2 directas (rechazadas como fuerte)
```json
[
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "New York 2:30",
    "direct_t2_neighbor": 7,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "New York 2:30",
    "direct_t2_neighbor": 9,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "New York 2:30",
    "direct_t2_neighbor": 22,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "New York 2:30",
    "direct_t2_neighbor": 29,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "New York 2:30",
    "direct_t2_neighbor": 42,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "New York 2:30",
    "direct_t2_neighbor": 44,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "New York 2:30",
    "direct_t2_neighbor": 53,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 35,
    "lottery": "New York 2:30",
    "direct_t2_neighbor": 63,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  }
]
```

### Ventanas (independientes)
- Siguiente sorteo: No
- Mismo día (otros sorteos): No
- Día calendario siguiente: Sí — 2026-07-23 Gana Mas pos 1 = 54 (ref 226103)
- Próximos 7 sorteos FEATURED: Sí — 2026-07-23 Gana Mas pos 1 = 54 (ref 226103)

### Explicación
35 (New York 2:30) genera candidato T1 54; confirmado por [14] vía Tabla2 (Loteria Nacional). Aparición posterior: 2026-07-23 Gana Mas pos 1 = 54 (ref 226103). Veredicto: ACIERTO_EXACTO.

---

## HIST-005 — full_day_first_positions

**Fecha:** 2017-12-27  
**Veredicto:** ACIERTO_NO_UNICO  
**Fuerte oficial:** `[9, 62]`  
**Único:** False  
**Manual (solo compare final):** None  
**Look-ahead bloqueado:** True

### Observados
- Gana Mas | hora=None | pos=1 (1ro) | número=92 | draw_id=d9c552aa-c2fd-4bf3-afe5-7673cec6534d | source_ref=163669
- Loteria Nacional | hora=None | pos=1 (1ro) | número=39 | draw_id=8954ce14-ae0d-4864-90b7-7e3e13243c7b | source_ref=109771
- New York 10:30 | hora=None | pos=3 (3ro) | número=2 | draw_id=5f53c0a9-dddd-4084-bf8e-d2f06df7b6d8 | source_ref=50667
- New York 2:30 | hora=None | pos=1 (1ro) | número=94 | draw_id=bee6e47c-f3d9-407c-972f-9344b3c33bd7 | source_ref=48204
- Quiniela Leidsa | hora=None | pos=1 (1ro) | número=53 | draw_id=d35d3f67-9777-414e-8ec9-a1642c0983d4 | source_ref=117301
- Quiniela Loteka | hora=None | pos=1 (1ro) | número=14 | draw_id=213a1a99-17c3-4fb2-b7a0-ee8e72b1d884 | source_ref=1864
- Quiniela Real | hora=None | pos=1 (1ro) | número=75 | draw_id=994ad367-9c95-4c31-a540-d3dec2cf5406 | source_ref=36619

### Fortalecidos oficiales
**Candidato 9**
- Generador (Tabla 1): 39 (Loteria Nacional)
- Compañeros T1 del generador: [9, 14, 30, 41, 46, 62, 78, 94]
- Grupo T2 del candidato: [7, 9, 22, 29, 35, 42, 44, 53, 63, 70, 90]
- Confirmadores: [53] via ['Quiniela Leidsa']
- Nivel: 1 confirmación(es)
- Confirmador nunca fortalecido: True
**Candidato 62**
- Generador (Tabla 1): 39 (Loteria Nacional)
- Compañeros T1 del generador: [9, 14, 30, 41, 46, 62, 78, 94]
- Grupo T2 del candidato: [62, 75]
- Confirmadores: [75] via ['Quiniela Real']
- Nivel: 1 confirmación(es)
- Confirmador nunca fortalecido: True

### Señales T2 directas (rechazadas como fuerte)
```json
[
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 92,
    "lottery": "Gana Mas",
    "direct_t2_neighbor": 27,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 92,
    "lottery": "Gana Mas",
    "direct_t2_neighbor": 68,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 92,
    "lottery": "Gana Mas",
    "direct_t2_neighbor": 76,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 39,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 78,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 2,
    "lottery": "New York 10:30",
    "direct_t2_neighbor": 20,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 94,
    "lottery": "New York 2:30",
    "direct_t2_neighbor": 58,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 94,
    "lottery": "New York 2:30",
    "direct_t2_neighbor": 84,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 53,
    "lottery": "Quiniela Leidsa",
    "direct_t2_neighbor": 7,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  }
]
```

### Ventanas (independientes)
- Siguiente sorteo: No
- Mismo día (otros sorteos): No
- Día calendario siguiente: Sí — 2017-12-28 Quiniela Loteka pos 2 = 62 (ref 1863)
- Próximos 7 sorteos FEATURED: Sí — 2017-12-28 Quiniela Loteka pos 2 = 62 (ref 1863)

### Explicación
39 (Loteria Nacional) genera candidato T1 9; confirmado por [53] vía Tabla2 (Quiniela Leidsa). 39 (Loteria Nacional) genera candidato T1 62; confirmado por [75] vía Tabla2 (Quiniela Real). Aparición posterior: 2017-12-28 Quiniela Loteka pos 2 = 62 (ref 1863). Veredicto: ACIERTO_NO_UNICO.

---

## HIST-006 — full_day_first_positions

**Fecha:** 2024-08-20  
**Veredicto:** ACIERTO_EXACTO  
**Fuerte oficial:** `68`  
**Único:** True  
**Manual (solo compare final):** None  
**Look-ahead bloqueado:** True

### Observados
- Gana Mas | hora=None | pos=1 (1ro) | número=47 | draw_id=24003345-12b8-4039-94f5-46529c1870f8 | source_ref=179765
- Loteria Nacional | hora=None | pos=1 (1ro) | número=23 | draw_id=5471e48a-c90e-4dcb-b449-758718d30349 | source_ref=179772
- New York 10:30 | hora=None | pos=1 (1ro) | número=16 | draw_id=ac1c53b6-cc1d-4a4f-8c05-05f3990ff25d | source_ref=179779
- New York 2:30 | hora=None | pos=1 (1ro) | número=10 | draw_id=75d5014d-46bd-4df1-8a1a-c1d6ce5f25dd | source_ref=179764
- Quiniela Leidsa | hora=None | pos=1 (1ro) | número=28 | draw_id=5e490750-5002-4fcd-9601-49f5a49b9ea8 | source_ref=179773
- Quiniela Loteka | hora=None | pos=1 (1ro) | número=78 | draw_id=a45ab40b-781a-4876-9f43-6a2f88ce02e9 | source_ref=179770
- Quiniela Real | hora=None | pos=1 (1ro) | número=92 | draw_id=b717ab9d-2dc8-45c8-bf22-2c3d00dfd69a | source_ref=179762

### Fortalecidos oficiales
**Candidato 68**
- Generador (Tabla 1): 47 (Gana Mas)
- Compañeros T1 del generador: [4, 36, 68, 79, 84]
- Grupo T2 del candidato: [27, 68, 76, 92]
- Confirmadores: [92] via ['Quiniela Real']
- Nivel: 1 confirmación(es)
- Confirmador nunca fortalecido: True

### Señales T2 directas (rechazadas como fuerte)
```json
[
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 23,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 28,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 23,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 73,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 23,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 77,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 23,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 87,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 16,
    "lottery": "New York 10:30",
    "direct_t2_neighbor": 25,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 10,
    "lottery": "New York 2:30",
    "direct_t2_neighbor": 1,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 10,
    "lottery": "New York 2:30",
    "direct_t2_neighbor": 100,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 28,
    "lottery": "Quiniela Leidsa",
    "direct_t2_neighbor": 23,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  }
]
```

### Ventanas (independientes)
- Siguiente sorteo: No
- Mismo día (otros sorteos): No
- Día calendario siguiente: Sí — 2024-08-21 Quiniela Loteka pos 2 = 68 (ref 179797)
- Próximos 7 sorteos FEATURED: Sí — 2024-08-21 Quiniela Loteka pos 2 = 68 (ref 179797)

### Explicación
47 (Gana Mas) genera candidato T1 68; confirmado por [92] vía Tabla2 (Quiniela Real). Aparición posterior: 2024-08-21 Quiniela Loteka pos 2 = 68 (ref 179797). Veredicto: ACIERTO_EXACTO.

---

## HIST-007 — full_day_first_positions

**Fecha:** 2023-05-24  
**Veredicto:** ACIERTO_NO_UNICO  
**Fuerte oficial:** `[2, 68, 87]`  
**Único:** False  
**Manual (solo compare final):** None  
**Look-ahead bloqueado:** True

### Observados
- Gana Mas | hora=None | pos=1 (1ro) | número=47 | draw_id=fd31a749-aece-45d9-bcb7-324ed6d1321f | source_ref=161915
- Loteria Nacional | hora=None | pos=1 (1ro) | número=23 | draw_id=c736bb6b-15f0-4a19-b2e2-01809e24d7da | source_ref=107955
- New York 10:30 | hora=None | pos=1 (1ro) | número=20 | draw_id=4d5edff3-27fa-4ab8-a500-9c3736d2faaf | source_ref=48693
- New York 2:30 | hora=None | pos=1 (1ro) | número=95 | draw_id=132109fd-36e9-4dea-9346-86ae333c3c88 | source_ref=46230
- Quiniela Leidsa | hora=None | pos=1 (1ro) | número=61 | draw_id=d69ec254-9d25-443c-a187-9e7be3c718b4 | source_ref=115440
- Quiniela Loteka | hora=None | pos=1 (1ro) | número=76 | draw_id=dd74f2f7-df5e-4e05-a001-84b09c67e6ac | source_ref=34683
- Quiniela Real | hora=None | pos=1 (1ro) | número=33 | draw_id=4449f0a7-b2b1-45cd-b1da-8da78517e095 | source_ref=34730

### Fortalecidos oficiales
**Candidato 2**
- Generador (Tabla 1): 33 (Quiniela Real)
- Compañeros T1 del generador: [2, 39, 82, 87]
- Grupo T2 del candidato: [2, 20]
- Confirmadores: [20] via ['New York 10:30']
- Nivel: 1 confirmación(es)
- Confirmador nunca fortalecido: True
**Candidato 68**
- Generador (Tabla 1): 47 (Gana Mas)
- Compañeros T1 del generador: [4, 36, 68, 79, 84]
- Grupo T2 del candidato: [27, 68, 76, 92]
- Confirmadores: [76] via ['Quiniela Loteka']
- Nivel: 1 confirmación(es)
- Confirmador nunca fortalecido: True
**Candidato 87**
- Generador (Tabla 1): 33 (Quiniela Real)
- Compañeros T1 del generador: [2, 39, 82, 87]
- Grupo T2 del candidato: [23, 28, 73, 77, 87]
- Confirmadores: [23] via ['Loteria Nacional']
- Nivel: 1 confirmación(es)
- Confirmador nunca fortalecido: True

### Señales T2 directas (rechazadas como fuerte)
```json
[
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 23,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 28,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 23,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 73,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 23,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 77,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 76,
    "lottery": "Quiniela Loteka",
    "direct_t2_neighbor": 27,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 76,
    "lottery": "Quiniela Loteka",
    "direct_t2_neighbor": 92,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  }
]
```

### Ventanas (independientes)
- Siguiente sorteo: No
- Mismo día (otros sorteos): No
- Día calendario siguiente: Sí — 2023-05-25 Quiniela Leidsa pos 1 = 68 (ref 115439)
- Próximos 7 sorteos FEATURED: Sí — 2023-05-25 Quiniela Leidsa pos 1 = 68 (ref 115439)

### Explicación
33 (Quiniela Real) genera candidato T1 2; confirmado por [20] vía Tabla2 (New York 10:30). 47 (Gana Mas) genera candidato T1 68; confirmado por [76] vía Tabla2 (Quiniela Loteka). 33 (Quiniela Real) genera candidato T1 87; confirmado por [23] vía Tabla2 (Loteria Nacional). Aparición posterior: 2023-05-25 Quiniela Leidsa pos 1 = 68 (ref 115439). Veredicto: ACIERTO_NO_UNICO.

---

## HIST-008 — full_day_first_positions

**Fecha:** 2017-09-30  
**Veredicto:** FALLO  
**Fuerte oficial:** `63`  
**Único:** True  
**Manual (solo compare final):** None  
**Look-ahead bloqueado:** True

### Observados
- Gana Mas | hora=None | pos=1 (1ro) | número=52 | draw_id=3680aa80-c597-466e-9a5c-2a225d185eec | source_ref=163749
- Loteria Nacional | hora=None | pos=1 (1ro) | número=38 | draw_id=54b49eeb-4b7d-4615-9ac6-bee1a7f13155 | source_ref=109857
- New York 10:30 | hora=None | pos=1 (1ro) | número=16 | draw_id=03c99498-8237-48eb-aef0-5374b0dcd49a | source_ref=50755
- New York 2:30 | hora=None | pos=1 (1ro) | número=60 | draw_id=917bfc28-c863-44e5-a51d-228edacd3d8e | source_ref=48292
- Quiniela Leidsa | hora=None | pos=1 (1ro) | número=90 | draw_id=ccf7942a-13d3-44eb-8ebc-c823b83f59ec | source_ref=117387
- Quiniela Loteka | hora=None | pos=1 (1ro) | número=4 | draw_id=f9325118-6d51-4d4a-96be-669797321ea5 | source_ref=1951
- Quiniela Real | hora=None | pos=1 (1ro) | número=77 | draw_id=c826a7e8-c840-4dcc-b4a7-b8be5435e9f3 | source_ref=36707

### Fortalecidos oficiales
**Candidato 63**
- Generador (Tabla 1): 38 (Loteria Nacional)
- Compañeros T1 del generador: [20, 31, 47, 52, 63, 100]
- Grupo T2 del candidato: [7, 9, 22, 29, 35, 42, 44, 53, 63, 70, 90]
- Confirmadores: [90] via ['Quiniela Leidsa']
- Nivel: 1 confirmación(es)
- Confirmador nunca fortalecido: True

### Señales T2 directas (rechazadas como fuerte)
```json
[
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 52,
    "lottery": "Gana Mas",
    "direct_t2_neighbor": 81,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 52,
    "lottery": "Gana Mas",
    "direct_t2_neighbor": 85,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 16,
    "lottery": "New York 10:30",
    "direct_t2_neighbor": 25,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 60,
    "lottery": "New York 2:30",
    "direct_t2_neighbor": 6,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 90,
    "lottery": "Quiniela Leidsa",
    "direct_t2_neighbor": 7,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 90,
    "lottery": "Quiniela Leidsa",
    "direct_t2_neighbor": 9,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 90,
    "lottery": "Quiniela Leidsa",
    "direct_t2_neighbor": 22,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 90,
    "lottery": "Quiniela Leidsa",
    "direct_t2_neighbor": 29,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  }
]
```

### Ventanas (independientes)
- Siguiente sorteo: No
- Mismo día (otros sorteos): No
- Día calendario siguiente: No
- Próximos 7 sorteos FEATURED: No

### Explicación
38 (Loteria Nacional) genera candidato T1 63; confirmado por [90] vía Tabla2 (Quiniela Leidsa). No apareció en ninguna ventana declarada. Veredicto: FALLO.

---

## HIST-009 — full_day_first_positions

**Fecha:** 2020-04-28  
**Veredicto:** SIN_CONFIRMACION  
**Fuerte oficial:** `null`  
**Único:** False  
**Manual (solo compare final):** None  
**Look-ahead bloqueado:** True

### Observados
- New York 10:30 | hora=None | pos=2 (2do) | número=99 | draw_id=97fc1f4c-4054-4ae0-8a9e-2efcbd65f3ab | source_ref=49814
- New York 2:30 | hora=None | pos=1 (1ro) | número=49 | draw_id=41702635-31ea-44da-9399-d4f5983ed568 | source_ref=47351

### Fortalecidos oficiales
_Ninguno_

### Señales T2 directas (rechazadas como fuerte)
```json
[]
```

### Ventanas (independientes)
- Siguiente sorteo: No
- Mismo día (otros sorteos): No
- Día calendario siguiente: No
- Próximos 7 sorteos FEATURED: No

### Explicación
Sin confirmación oficial: ningún compañero T1 fue confirmado por otro observado.

---

## HIST-010 — full_day_first_positions

**Fecha:** 2023-04-14  
**Veredicto:** DIRECT_T2_RECHAZADO  
**Fuerte oficial:** `null`  
**Único:** False  
**Manual (solo compare final):** None  
**Look-ahead bloqueado:** True

### Observados
- Gana Mas | hora=None | pos=1 (1ro) | número=24 | draw_id=27d5db09-5bb9-4d4d-8a26-f27386cf5146 | source_ref=161954
- Loteria Nacional | hora=None | pos=1 (1ro) | número=52 | draw_id=c7979e33-4a1a-4fbd-a216-54edeb985b6a | source_ref=107995
- New York 10:30 | hora=None | pos=1 (1ro) | número=34 | draw_id=b7b48f95-7b6a-4688-9105-544d52d33723 | source_ref=48733
- New York 2:30 | hora=None | pos=1 (1ro) | número=86 | draw_id=0412a071-1408-42a8-95cb-30dcd33271dc | source_ref=46270
- Quiniela Leidsa | hora=None | pos=1 (1ro) | número=15 | draw_id=098358c8-9ee6-4136-8228-ed74900b7912 | source_ref=115480
- Quiniela Loteka | hora=None | pos=1 (1ro) | número=45 | draw_id=9da6d135-bc19-49ec-93ef-3137e73864f5 | source_ref=29
- Quiniela Real | hora=None | pos=1 (1ro) | número=87 | draw_id=b32c2e89-f3ec-4eeb-8841-411b0467d765 | source_ref=34770

### Fortalecidos oficiales
_Ninguno_

### Señales T2 directas (rechazadas como fuerte)
```json
[
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 52,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 81,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 52,
    "lottery": "Loteria Nacional",
    "direct_t2_neighbor": 85,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 34,
    "lottery": "New York 10:30",
    "direct_t2_neighbor": 26,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 34,
    "lottery": "New York 10:30",
    "direct_t2_neighbor": 59,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 34,
    "lottery": "New York 10:30",
    "direct_t2_neighbor": 72,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 86,
    "lottery": "New York 2:30",
    "direct_t2_neighbor": 19,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 86,
    "lottery": "New York 2:30",
    "direct_t2_neighbor": 46,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 15,
    "lottery": "Quiniela Leidsa",
    "direct_t2_neighbor": 96,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  }
]
```

### Ventanas (independientes)
- Siguiente sorteo: No
- Mismo día (otros sorteos): No
- Día calendario siguiente: No
- Próximos 7 sorteos FEATURED: No

### Explicación
No hay candidato T1 confirmado. Señal T2 directa rechazada (52→81). No es fuerte oficial.

---

## HIST-011 — C2_direct_t2_rejected

**Fecha:** 2026-06-21  
**Veredicto:** DIRECT_T2_RECHAZADO  
**Fuerte oficial:** `null`  
**Único:** False  
**Manual (solo compare final):** 75  
**Look-ahead bloqueado:** True

### Observados
- Gana Mas | hora=None | pos=1 (1ro) | número=41 | draw_id=d6732010-5902-4533-a13c-2fb016cf6856 | source_ref=224681
- Quiniela Loteka | hora=None | pos=1 (1ro) | número=62 | draw_id=fb1e9073-070f-4cf1-a487-56c6aa9e478e | source_ref=224700

### Fortalecidos oficiales
_Ninguno_

### Señales T2 directas (rechazadas como fuerte)
```json
[
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 41,
    "lottery": "Gana Mas",
    "direct_t2_neighbor": 12,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 41,
    "lottery": "Gana Mas",
    "direct_t2_neighbor": 56,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 41,
    "lottery": "Gana Mas",
    "direct_t2_neighbor": 71,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 41,
    "lottery": "Gana Mas",
    "direct_t2_neighbor": 89,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  },
  {
    "classification": "DIRECT_T2_NEIGHBOR_SIGNAL",
    "observed": 62,
    "lottery": "Quiniela Loteka",
    "direct_t2_neighbor": 75,
    "is_official_fuerte": false,
    "rejected_as_predictive_rule": true
  }
]
```

### Ventanas (independientes)
- Siguiente sorteo: No
- Mismo día (otros sorteos): No
- Día calendario siguiente: No
- Próximos 7 sorteos FEATURED: No

### Explicación
Manual 75 no es fuerte oficial. 62→75 es DIRECT_T2_NEIGHBOR_SIGNAL rechazada. No hay candidato T1 confirmado. Señal T2 directa rechazada (41→12). No es fuerte oficial.
