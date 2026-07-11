# PLAN_DE_DESPLIEGUE — Justech Fiscal v1.0 → Producción

**Destino:** `justgroup.app` (solo tras aprobación explícita)  
**Origen certificado:** `erp.justech.do` / `justech_dev` / rama `feature/fiscal-standard-consolidation`  
**Prohibido:** merge improvisado, hotfixes directos en PROD, compartir filestore/BD entre entornos.

---

## Ventana de mantenimiento

| Ítem | Valor sugerido |
|------|----------------|
| Día | Fin de semana o día pactado con Contabilidad |
| Hora | 22:00–02:00 AST |
| Duración estimada | **90–150 minutos** |
| Congelamiento | Sin facturación/pagos durante la ventana |

---

## Responsables

| Rol | Responsabilidad |
|-----|-----------------|
| Propietario / Sponsor | Aprobación explícita de despliegue |
| Arquitecto / DevOps | Backup, deploy, restore readiness |
| Contador / Responsable Fiscal | Validación funcional post |
| Admin Sistema | Usuarios, crons, correo |

---

## Orden de pasos

1. **Congelar** rama release y etiquetar (SemVer módulos Justech).
2. **Auditoría pre-prod** de `justgroup.app` (solo lectura): módulos, versiones, crons, NCF, padrón.
3. **Backup completo PROD** (BD + filestore) y validar listado `pg_restore -l` + tamaño filestore.
4. **Clonar evidencia** del backup (ruta documentada en ticket).
5. **Merge controlado** `feature/fiscal-standard-consolidation` → `development` → `release/*` → `main` (solo con aprobación; este plan no ejecuta merge).
6. **Sync addons** al servidor PROD (rsync/git pull según procedimiento oficial).
7. **Upgrade módulos** Justech en orden de dependencias (`justech_l10n_do_base` → `ncf` → `reports` → `payments` → `treasury` → `fiscal_admin`).
8. **Activar crons PROD:** padrón DGII, secuencias fiscales, currency, mail queue (si SMTP listo).
9. **Asignar grupos** Contador = Responsable Fiscal (matriz roles).
10. **Smoke post** (ver `CHECKLIST_POST_PRODUCCION.md`).
11. **Apertura** operativa y monitoreo 72h (`PLAN_ESTABILIZACION.md`).

---

## Duración por fase

| Fase | Minutos |
|------|---------|
| Backup + validación | 30–45 |
| Deploy código + upgrade | 30–45 |
| Config crons/roles/SMTP | 15–20 |
| Smoke funcional | 20–30 |
| Buffer | 15 |

---

## Criterio de abortar (rollback)

Cualquier fallo de upgrade, pérdida de acceso, NCF no asignable, padrón vacío, o GL descuadrado en smoke → ejecutar `PLAN_DE_ROLLBACK.md` inmediatamente.
