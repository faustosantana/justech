# Centro de Administración de Lottery IA — entrega

**Ruta:** https://jaios.justech.do → `/lottery/admin/ai`  
**Imágenes:** `jaios-app-backend:aiadmin-20260723`, `jaios-app-frontend:aiadmin-20260723`  
**Rollback:** `pre-aiadmin-20260723`  
**Backup:** `/var/jaios/backups/pre_lottery_aiadmin_20260723220736.dump`  
**Migración:** `059_lottery_ai_admin_center` aplicada  
**Commits:** `dd19094`, `a19793a`, `20d4111` (+ bake overlay)

## UAT
- Safety tests: **9/9 PASS** (incluye caso permanente «esas loterías»)
- Memoria prod: turn 3 = `post_occurrence_window` con 2× following_days, sin pedir fecha
- Hermes: **No utilizado como orquestador**
- Prompt activo: **v2** (DB seed; v3 draft)
- Sync: Leidsa + Loteka + Nacional only

## Pendiente / riesgos
- Alertas proactivas aún sin scheduler de detección continua
- Publicación de prompt bloqueada por P0/P1 de benchmark, pero el suite completo ≥250 sigue pendiente
- Editor de prompts por bloques/plantillas: cuerpo completo + metadata; plantillas nombradas aún parciales
- Activación Hermes orquestador: gate documentado, no activado
