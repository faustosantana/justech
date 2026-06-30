# Checklist de Producción — Go-Live

**Versión:** 1.0 Fase 10  
**Uso:** Ejecutar secuencialmente en ventana de mantenimiento aprobada

---

## Fase 0 — Pre-vuelo (T-7 días)

| # | Paso | Responsable | ✓ |
|---|------|-------------|---|
| 0.1 | Aprobación escrita Go-Live | Hellenia | ☐ |
| 0.2 | Comunicar ventana mantenimiento usuarios | Hellenia | ☐ |
| 0.3 | Backup triple (DEV/TEST/odoo-pecv) | Justech | ☐ |
| 0.4 | Verificar integridad backups | Justech | ☐ |
| 0.5 | Rangos NCF DGII cargados en plantilla | Contabilidad | ☐ |
| 0.6 | SMTP corporativo probado | Justech | ☐ |
| 0.7 | Usuarios ROLE_MATRIX creados (en staging) | Justech | ☐ |
| 0.8 | Plan rollback impreso/disponible | Justech | ☐ |

---

## Fase 1 — Preparación stack (T-1 día)

| # | Paso | ✓ |
|---|------|---|
| 1.1 | Crear `config/production/.env` desde ejemplo | ☐ |
| 1.2 | Crear `config/production/odoo.conf` (workers=2) | ☐ |
| 1.3 | `docker compose -f docker/production/docker-compose.yml config` | ☐ |
| 1.4 | Desplegar BD + Odoo **sin** router Traefik público | ☐ |
| 1.5 | Crear BD `hellenia_prod` | ☐ |
| 1.6 | Instalar Enterprise + módulos Justech MVP | ☐ |
| 1.7 | Aplicar parametrización Fase 8 | ☐ |
| 1.8 | Registrar licencia Enterprise | ☐ |
| 1.9 | Crear `it@justech.do` + usuarios funcionales | ☐ |
| 1.10 | Smoke test interno (sin DNS público) | ☐ |

---

## Fase 2 — Ventana de corte (T-0)

| # | Paso | Tiempo est. | ✓ |
|---|------|-------------|---|
| 2.1 | Anunciar inicio mantenimiento | 0 min | ☐ |
| 2.2 | **Backup final odoo-pecv** | 15 min | ☐ |
| 2.3 | Detener escritura usuarios en odoo-pecv (comunicar) | — | ☐ |
| 2.4 | Export datos maestros si migración desde legacy | 30–120 min | ☐ |
| 2.5 | Import clientes/proveedores/productos (si aplica) | 60–180 min | ☐ |
| 2.6 | Validar parametrización producción | 30 min | ☐ |
| 2.7 | Activar labels Traefik `odoo.hellenia.cloud` | 5 min | ☐ |
| 2.8 | Verificar certificado Let's Encrypt emitido | 5 min | ☐ |
| 2.9 | Establecer `web.base.url` producción | 2 min | ☐ |
| 2.10 | **NO cambiar DNS** si ya apunta al VPS — solo router | — | ☐ |

---

## Fase 3 — Validación (T+0 a T+2h)

| # | Paso | ✓ |
|---|------|---|
| 3.1 | Login cada rol funcional | ☐ |
| 3.2 | Ciclo venta completo + NCF real | ☐ |
| 3.3 | Ciclo compra + NCF | ☐ |
| 3.4 | Reportes 606/607 | ☐ |
| 3.5 | PDF factura con logo | ☐ |
| 3.6 | Cobro y conciliación | ☐ |
| 3.7 | Contador valida trazabilidad | ☐ |
| 3.8 | Firma acta Go-Live | ☐ |

---

## Fase 4 — Post-activación (T+24h)

| # | Paso | ✓ |
|---|------|---|
| 4.1 | Monitoreo logs Odoo/Traefik/PostgreSQL | ☐ |
| 4.2 | Backup automático producción verificado | ☐ |
| 4.3 | odoo-pecv en modo solo lectura o detenido (decisión) | ☐ |
| 4.4 | Comunicar URL oficial usuarios | ☐ |
| 4.5 | Soporte según POST_GO_LIVE_SUPPORT_PLAN | ☐ |

---

## Fase 5 — Rollback (si necesario)

Ver [ROLLBACK_PLAN.md](ROLLBACK_PLAN.md) — decisión en < 4 horas.

| Trigger rollback | Acción |
|------------------|--------|
| Smoke test FAIL crítico | Restaurar odoo-pecv, desactivar router hellenia-prod |
| NCF / fiscal FAIL | Rollback + análisis |
| Performance inaceptable | Escalar workers o postponer |

---

## Estado Fase 10

Checklist **construido y certificado** — ejecución pendiente aprobación.

**Estado bloque 7:** PASS
