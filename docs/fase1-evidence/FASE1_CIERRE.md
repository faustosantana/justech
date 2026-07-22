# Fase 1 — Cierre `process_requirements`

**Fecha:** 2026-06-25  
**Estado:** **PASS** (22/22)  
**Procesos QA:** DGII-CCC-PEEX-2026-0005 · RESIDE-DAF-CD-2026-0037  

---

## Configuración activa en producción

```env
DGCP_REQUIREMENTS_TABLE_READ=true
DGCP_REQUIREMENTS_TABLE_WRITE=true
```

Migración: `050_process_requirements`  
Backfill DGII: 27 filas · Backfill RESIDE: 13 filas  

---

## Tabla de validación

| Prueba | Resultado esperado | Resultado real | PASS/FAIL |
|--------|-------------------|----------------|-----------|
| Activar flags READ/WRITE | true / true | READ=True WRITE=True | **PASS** |
| Backend con código Fase 1 | endpoints preparation/requirements | ProcessRequirementService import OK | **PASS** |
| DGII tabla process_requirements | 27 requisitos | 27 | **PASS** |
| DGII dual-read checklist | total=27 desde tabla | checklist=27 prep=27 jsonb=27 | **PASS** |
| DGII Checklist vs Documentos Justech | mismos estados por key | 27 ítems alineados | **PASS** |
| DGII RPE/DGII/TSS detectados | claves corporativas presentes | certificacion_dgii, certificacion_tss, rpe | **PASS** |
| Actualizar estado requisito (PATCH) | 200 + needs_review | needs_review | **PASS** |
| Persistencia en process_requirements | status=needs_review | needs_review | **PASS** |
| Asociar/reemplazar documento | evidencia previa o 200 | evidencia en rpe doc=True | **PASS** |
| RESIDE backfill/tabla | >=13 requisitos | 13 | **PASS** |
| RESIDE checklist carga | HTTP 200 + items>0 | total=13 | **PASS** |
| RESIDE Checklist vs Justech | alineados | 13 ítems alineados | **PASS** |
| Rollback OFF — checklist JSONB | total=27 (legacy) | checklist=27 | **PASS** |
| Rollback OFF — fuente legacy | prep sigue accesible | prep total=27 | **PASS** |
| Re-encender READ — vuelve tabla | total=27 | checklist=27 | **PASS** |
| Requisitos (Hermes) | HTTP 200 | 200 | **PASS** |
| Checklist | HTTP 200 | 200 | **PASS** |
| Documentos Justech | HTTP 200 | 200 | **PASS** |
| Bid package / expediente | HTTP 200 | 200 | **PASS** |
| Histórico | HTTP 200 | 200 | **PASS** |
| Flujo interés / ficha | HTTP 200 + status | awarded | **PASS** |
| Formularios | HTTP 200 | 200 | **PASS** |

---

## Rollback Fase 1

```bash
# .env
DGCP_REQUIREMENTS_TABLE_READ=false
DGCP_REQUIREMENTS_TABLE_WRITE=false

docker compose up -d backend
```

Comportamiento: vuelve lectura/escritura JSONB legacy. Tabla `process_requirements` se ignora (no se borra).

Reactivar:

```bash
DGCP_REQUIREMENTS_TABLE_READ=true
DGCP_REQUIREMENTS_TABLE_WRITE=true
docker compose up -d backend
```

---

## Script QA reproducible

```bash
docker exec jaios-app-backend-1 python /app/scripts/fase1_process_requirements_qa.py
```

Backfill manual:

```bash
docker exec jaios-app-backend-1 python -m app.scripts.backfill_process_requirements <opportunity_uuid>
```

---

## Notas

- JSONB legacy (`checklist`, `requirements`, `document_matches`) **intacto** — dual-write mantiene sincronía.
- Tab Requisitos (Hermes) sigue leyendo JSONB `requirements` (plan Fase 5).
- Autollenado universal **no modificado**.
- **Fase 2 no iniciada** — pendiente aprobación explícita post-PASS.

---

## Deuda técnica

- Código Fase 1 desplegado en contenedor vía `docker cp`; **rebuild de imagen backend** recomendado para persistir en imagen.
- Dual-read no ejecuta reconcile en cada GET (evita drift con imagen prod); matching sigue en flujo analyze/legacy.
