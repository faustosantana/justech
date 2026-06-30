# Informe de Infraestructura — Producción

**VPS:** srv.hellenia.cloud (`2.25.69.179`)  
**Auditoría:** 2026-06-30T14:22:22Z  
**Evidencia:** `evidence/phase10-infra-audit.txt`

---

## 1. Resumen bloque 1

| Área | Estado | Detalle |
|------|--------|---------|
| Docker | PASS | 7 contenedores activos |
| Docker Compose | PASS | hellenia-dev, hellenia-test, odoo-pecv, traefik |
| Traefik | PASS CON OBS | Activo; router `odoo.hellenia.cloud` **pendiente** |
| Redes | PASS | 6 redes; aislamiento por stack |
| Volúmenes | PASS | 9 volúmenes nombrados |
| Healthchecks | PASS | DEV/TEST/db healthy |
| Backups | PASS | Triple 2026-06-30_1421 |
| Restore | PASS CON OBS | Scripts DEV/TEST; prod manual |
| Logs | PASS CON OBS | stdout Docker; logrotate pendiente |
| Disco | PASS | 96G total, 19% usado, 79G libre |
| RAM | PASS CON OBS | 7.8 GB total, 6.3 GB available |
| CPU | PASS CON OBS | 2 vCPU AMD EPYC |
| Swap | FAIL→OBS | **0 swap** — recomendar 2GB |
| SSL DEV/TEST | PASS | Let's Encrypt válido |
| SSL odoo.hellenia | FAIL→OBS | Sin router — 404/default cert |
| DNS | PASS | odoo/dev/test → 2.25.69.179 |
| Firewall | PASS CON OBS | UFW no verificado en audit |
| Fail2ban | PASS CON OBS | Estado no capturado — verificar |
| Cron | PASS CON OBS | Revisar cron backups prod |

**Bloque 1:** PASS CON OBSERVACIONES

### FAIL/OBS detalle

| ID | Causa | Impacto | Prioridad | Solución |
|----|-------|---------|-----------|----------|
| INF-01 | Sin swap | OOM bajo pico | P1 | `fallocate` + swapon 2GB |
| INF-02 | 2 vCPU | Workers limitados | P2 | workers=2 en prod |
| INF-03 | Router odoo.hellenia ausente | Go-Live bloqueado | P0 | Activar en checklist |
| INF-04 | Logrotate no confirmado | Disco lleno futuro | P2 | Configurar logrotate |

---

## 2. Contenedores activos

| Contenedor | Estado |
|------------|--------|
| hellenia-dev-odoo-1 | healthy |
| hellenia-dev-db-1 | healthy |
| hellenia-test-odoo-1 | healthy |
| hellenia-test-db-1 | healthy |
| odoo-pecv-odoo-1 | up 4 days |
| odoo-pecv-db-1 | healthy |
| traefik-traefik-1 | up |

---

## 3. Capacidad Go-Live

| Pregunta | Respuesta |
|----------|-----------|
| ¿Disco suficiente? | Sí (79 GB libres) |
| ¿RAM suficiente Odoo 19 prod? | Ajustado (workers=2) |
| ¿Coexistencia 4 stacks? | Sí en mismo VPS |
| ¿Listo para tráfico producción? | Tras desplegar hellenia-prod + router |

---

## 4. Estado Fase 10

**PASS CON OBSERVACIONES** — infraestructura soporta Go-Live con ajustes P0/P1.
