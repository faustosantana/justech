# Plan de Rollback — Go-Live

**Versión:** 2.0 (Fase 10)  
**RTO objetivo:** < 4 horas  
**RPO objetivo:** Backup final pre-corte (`odoo-pecv`)

---

## 1. Cuándo activar rollback

| Severidad | Criterio | Ejemplo |
|-----------|----------|---------|
| P0 | Sistema inoperante o fiscal inválido | NCF duplicados en producción real |
| P0 | Pérdida datos financieros | Asientos no balanceados masivos |
| P1 | Performance crítica sin mitigación rápida | OOM repetido |
| P2 | Defecto funcional no bloqueante | Reporte formato parcial — no rollback |

**Decisión:** Gerencia Hellenia + Justech IT.

---

## 2. Rollback infraestructura

| Componente | Acción | Tiempo est. |
|------------|--------|-------------|
| DNS | **No cambiar** si solo se activó router — desactivar router `hellenia-prod` | 5 min |
| Traefik | `docker compose stop` hellenia-prod o quitar labels | 5 min |
| SSL | Revertir a odoo-pecv router existente | Automático |
| Docker hellenia-prod | `docker compose down` (preservar volúmenes) | 10 min |
| odoo-pecv | `docker compose up -d` si fue detenido | 10 min |

---

## 3. Rollback base de datos

### Producción nueva (`hellenia_prod`)

- **No restaurar sobre odoo-pecv** — son stacks separados
- Preservar volumen `hellenia-prod_db` para análisis forense
- Rollback operativo = volver a **odoo-pecv** como sistema activo

### odoo-pecv (legacy)

```bash
# Restaurar desde backup Fase 10
BACKUP=/opt/odoo-projects/hellenia/backups/production/2026-06-30_1421
docker compose -f /docker/odoo-pecv/docker-compose.yml stop odoo
# Restaurar postgres_all.sql.gz + filestore según procedimiento DBA
docker compose -f /docker/odoo-pecv/docker-compose.yml up -d
```

---

## 4. Rollback filestore

| Stack | Volumen | Backup |
|-------|---------|--------|
| odoo-pecv | `odoo-pecv_odoo-data` | `backups/production/<TS>/filestore.tar.gz` |
| hellenia-prod | `hellenia-prod_odoo-data` | Backup post-deploy (configurar) |

---

## 5. Rollback NCF / fiscal

| Escenario | Acción |
|-----------|--------|
| NCF emitidos en prod nueva antes de rollback | Documentar secuencias consumidas; coordinar con contador/DGII |
| Rangos cargados incorrectamente | No void masivo sin análisis — restaurar BD prod si pre-corte |
| Reportes 606/607 enviados | Rollback operativo no revierte declaraciones — escalar contador |

---

## 6. Rollback usuarios

- Usuarios en `hellenia_prod` no afectan `odoo-pecv`
- Credenciales odoo-pecv legacy permanecen en backup

---

## 7. Orden de ejecución rollback

1. Comunicar rollback a stakeholders  
2. Desactivar `hellenia-prod` en Traefik  
3. Verificar `odoo-pecv` operativo  
4. Si odoo-pecv corrupto → restaurar backup `2026-06-30_1421` o más reciente  
5. Smoke test odoo-pecv  
6. Comunicar URL legacy a usuarios  
7. Post-mortem en 48h  

---

## 8. Estado Fase 10

**PASS** — plan documentado, no probado en ejecución (recomendado drill en piloto).

**Evidencia backup rollback:** `backups/production/2026-06-30_1421`
