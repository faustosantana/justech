# Production Deploy Checklist — Motor de Relaciones Numéricas

**Estado:** plantilla lista. **No ejecutar** hasta autorización expresa de Producción.  
**Fecha plantilla:** 2026-07-24  
**Rama / commits:** ver `RELEASE_NOTES_NUMERIC_RELATIONS_RC.md`

---

## Precondiciones

- [ ] Veredicto GO (o GO CONDICIONADO con pendientes aceptados por escrito)
- [ ] Autorización expresa de despliegue a Producción
- [ ] Ventana de mantenimiento acordada
- [ ] Owner on-call identificado
- [ ] Confirmación: **no** se modificará el sincronizador en este deploy
- [ ] Confirmación: no fusión/borrado de draws duplicados

---

## 1. Backup BD

- [ ] Dump lógico PostgreSQL producción (schema `jaios` / DB lottery)
- [ ] Verificar tamaño e integridad del dump
- [ ] Guardar ruta/hash del backup: `________________________`
- [ ] Retención mínima 7 días

## 2. Snapshot VPS

- [ ] Snapshot del VPS / volumen de aplicación
- [ ] ID snapshot: `________________________`
- [ ] Probado el procedimiento de restore (al menos documentado)

## 3. Validación rollback

- [ ] Tag `restore/lottery-pre-numeric-relations-motor-20260723` accesible
- [ ] Commit objetivo rollback: `25ccd8aa` (o el tag vigente al momento del deploy)
- [ ] Procedimiento de redeploy al tag ensayado en DEV/RC
- [ ] Criterio de activación de rollback escrito

## 4. Migraciones

- [ ] Revisar alembic pendientes vs prod
- [ ] Aplicar solo migraciones necesarias para modelo lottery (sin sync write)
- [ ] Verificar columnas usadas por NR / AI usage si chat en prod
- [ ] Registrar versión post-migrate: `________________________`

## 5. Restart servicios

- [ ] Desplegar backend con commits RC
- [ ] Desplegar frontend con ruta `/lottery/admin/numeric-relations`
- [ ] `LOTTERY_MODULE_ENABLED=true`
- [ ] Sync write flags **off** salvo autorización distinta
- [ ] Restart API + workers + frontend
- [ ] Healthcheck OK

## 6. Smoke test producción

- [ ] CASO 1: analizar 26 en Leidsa (ocurrencias, `draw_id`, score 0 visibles)
- [ ] CASO 2: analizar 34 todas (ranking/score/traza/metadata)
- [ ] CASO 3: analizar 45 en Leidsa y Loteka **con K explícito** (una sola llamada, consolidado)
- [ ] CASO 4: usuario sin permiso → 403 auditoría
- [ ] CASO 5: “Analiza el 26” → pide solo faltantes (lotería / K), sin inventar

## 7. Verificación API

- [ ] `GET /lottery/admin/numeric-relations/tables` (admin)
- [ ] `GET /lottery/admin/numeric-relations/groups`
- [ ] `POST /lottery/admin/numeric-relations/analyze`
- [ ] OpenAPI / health

## 8. Verificación chat

- [ ] Tool `lottery_analyze_numeric_relations` invocada
- [ ] Huawei no calcula tablas/códigos/vecinos
- [ ] Disclaimer de señal histórica presente
- [ ] Multi-lotería con K → un solo resultado

## 9. Verificación UI

- [ ] Tabla 1 y Tabla 2 separadas
- [ ] Ranking legible + score 0
- [ ] Trazas expandibles
- [ ] Metadata dedupe visible
- [ ] Sin JSON bruto en vista principal

## 10. Validación draw_id

- [ ] Ocurrencias listan `draw_id` distintos
- [ ] Peers no mezclan números de otros `draw_id`
- [ ] Duplicados de contenido (si hay) permanecen separados

## 11. Validación permisos

- [ ] Admin autorizado: acceso auditoría
- [ ] No autorizado: UI denegada **y** API 403
- [ ] No basta ocultar el menú

## 12. Validación logs

- [ ] Sin errores 500 en analyze/chat NR
- [ ] Sin escrituras sync no autorizadas
- [ ] Latencia chat/analyze aceptable

## 13. Plan de rollback

1. Anunciar rollback.
2. Redeploy al tag `restore/lottery-pre-numeric-relations-motor-20260723`.
3. Restart servicios.
4. Smoke: login + lottery home (sin depender de NR).
5. Si corrupción de datos (no esperada): restaurar dump BD.
6. Postmortem en 24 h.

**Contactos rollback:** `________________________`

---

## Firma

| Rol | Nombre | Fecha | Firma |
|-----|--------|-------|-------|
| Deployer | | | |
| Approver | | | |
| QA / UAT | | | |
