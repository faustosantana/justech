# Go-Live Readiness — odoo.hellenia.cloud

**Cliente:** Hellenia, S.R.L.  
**Fecha:** 2026-06-30  
**Fase:** 7.5 — Administración, Seguridad y Preparación Operativa  
**URL objetivo:** https://odoo.hellenia.cloud  
**Estado:** **SUPERSEDIDO POR FASE 10 — ver [GO_LIVE_MASTER_PLAN.md](GO_LIVE_MASTER_PLAN.md)**

> **Actualización Fase 10 (2026-06-30):** UAT completado (APTO PARA PILOTO). Preparación Go-Live documentada. Clasificación actual: **APTO PARA GO-LIVE CON OBSERVACIONES**. Go-Live **no ejecutado**.

---

## 1. Resumen ejecutivo

| Dimensión | Estado | Bloqueante Go-Live |
|-----------|--------|-------------------|
| DNS `odoo.hellenia.cloud` | ✅ Listo | No |
| Router Traefik producción | ❌ No configurado | **Sí** |
| Certificado TLS Let's Encrypt | ❌ Solo default Traefik | **Sí** |
| Stack Odoo 19 Enterprise PROD | ❌ No desplegado | **Sí** |
| Base de datos producción | ❌ No creada | **Sí** |
| Licencia Enterprise PROD | ❌ Pendiente migración | **Sí** |
| Usuarios funcionales Hellenia | ❌ No creados (diseño listo) | **Sí** |
| UAT funcional | ❌ No iniciado | **Sí** |
| SMTP corporativo | ❌ Pendiente | Recomendado |
| Stack legacy `odoo-pecv` | ✅ Operativo sin cambios | N/A |

**Veredicto:** La infraestructura de desarrollo y pruebas está lista para UAT. La producción en `odoo.hellenia.cloud` requiere un proyecto de despliegue separado antes del Go-Live.

---

## 2. Producción actual vs objetivo

| Componente | Producción actual | Objetivo Go-Live |
|------------|-------------------|------------------|
| Stack Docker | `odoo-pecv` (Odoo **18**) | `hellenia-prod` (Odoo **19** Enterprise) |
| Dominio activo | `odoo-pecv.srv1784296.hstgr.cloud` | `odoo.hellenia.cloud` |
| Base de datos | PostgreSQL en `odoo-pecv-db-1` | Nueva BD `hellenia_prod` (propuesto) |
| Módulos Justech | No instalados | `justech_l10n_do_*` MVP |
| Licencia Enterprise | Odoo 18 legacy | Código `M260616306091776` (política un código / una BD) |
| VPS | `2.25.69.179` / `srv.hellenia.cloud` | Mismo VPS |

**Regla Fase 7.5:** No detener, migrar ni modificar `odoo-pecv` hasta backup completo y aprobación explícita de Hellenia / Justech.

---

## 3. Verificaciones de infraestructura (solo lectura)

### 3.1 DNS

| Registro | Valor | Estado |
|----------|-------|--------|
| `odoo.hellenia.cloud` A | `2.25.69.179` | ✅ |
| `dev.hellenia.cloud` A | `2.25.69.179` | ✅ |
| `test.hellenia.cloud` A | `2.25.69.179` | ✅ |

### 3.2 Traefik

| Verificación | DEV | TEST | PROD futura |
|--------------|-----|------|-------------|
| Contenedor activo | ✅ | ✅ | N/A |
| Router Host | `dev.hellenia.cloud` | `test.hellenia.cloud` | ❌ **No existe** |
| Entrypoint `websecure` | ✅ | ✅ | Pendiente |
| TLS resolver `letsencrypt` | ✅ | ✅ | Pendiente |
| HTTP → HTTPS redirect | ✅ | ✅ | ✅ (global) |
| Puerto servicio Odoo | 8069 | 8069 | 8069 |

Routers Odoo activos hoy:

| Router | Host |
|--------|------|
| `hellenia-dev` | `dev.hellenia.cloud` |
| `hellenia-test` | `test.hellenia.cloud` |
| `odoo-pecv` | `odoo-pecv.srv1784296.hstgr.cloud` |

### 3.3 HTTPS / certificados

| Dominio | Emisor | Estado |
|---------|--------|--------|
| `dev.hellenia.cloud` | Let's Encrypt | ✅ Válido hasta 2026-09-27 |
| `test.hellenia.cloud` | Let's Encrypt | ✅ Válido hasta 2026-09-27 |
| `odoo.hellenia.cloud` | Traefik Default Cert | ⚠️ Sin router LE — HTTP **404** |

### 3.4 Comparativa ambientes

| URL | Login HTTP | TLS LE | `web.base.url` | BD |
|-----|------------|--------|----------------|-----|
| https://dev.hellenia.cloud | 200 | ✅ | `https://dev.hellenia.cloud` | `hellenia_dev` |
| https://test.hellenia.cloud | 200 | ✅ | `https://test.hellenia.cloud` | `hellenia_test` |
| https://odoo.hellenia.cloud | 404 | ❌ default | N/A | N/A |

---

## 4. Checklist Go-Live (orden sugerido)

### Fase A — Pre-requisitos de negocio

| # | Item | Responsable | Estado |
|---|------|-------------|--------|
| A1 | UAT funcional completado y firmado | Hellenia + Justech | ⏳ |
| A2 | Matriz de roles aprobada | Hellenia | ✅ Diseño en [ROLE_MATRIX.md](ROLE_MATRIX.md) |
| A3 | Usuarios funcionales creados según matriz | Justech | ⏳ Post-UAT |
| A4 | Datos maestros cargados (clientes, productos, plan contable) | Hellenia | ⏳ |
| A5 | Rangos NCF DGII cargados y validados | Hellenia / Contabilidad | ⏳ |
| A6 | SMTP corporativo configurado y probado | Justech + Hellenia IT | ⏳ |
| A7 | Política de contraseñas / 2FA definida | Hellenia | ⏳ |

### Fase B — Infraestructura producción Odoo 19

| # | Item | Prioridad | Estado |
|---|------|-----------|--------|
| B1 | Backup completo `odoo-pecv` (BD + filestore) | P0 | ⏳ |
| B2 | Definir directorio `docker/production/` o evolución imagen Enterprise | P0 | ⏳ |
| B3 | Crear BD `hellenia_prod` con módulos MVP | P0 | ⏳ |
| B4 | Configurar `config/production/odoo.conf` (`proxy_mode`, `dbfilter`) | P0 | ⏳ |
| B5 | Desplegar stack `hellenia-prod` sin exponer hasta validación interna | P0 | ⏳ |
| B6 | Añadir labels Traefik para `odoo.hellenia.cloud` | P0 | ⏳ |
| B7 | Emitir certificado Let's Encrypt (primera petición HTTPS) | P0 | ⏳ |
| B8 | Establecer `web.base.url` = `https://odoo.hellenia.cloud` | P0 | ⏳ |
| B9 | Registrar licencia Enterprise en BD producción | P0 | ⏳ |
| B10 | Configurar backups automáticos producción | P0 | ⏳ |
| B11 | Configurar logrotate / monitoreo | P1 | ⏳ |

### Fase C — Seguridad y operación

| # | Item | Prioridad | Estado |
|---|------|-----------|--------|
| C1 | Crear `it@justech.do` en PROD (mismos grupos que DEV/TEST) | P0 | ⏳ |
| C2 | Restringir `admin` a uso emergencia documentado | P1 | ⏳ |
| C3 | Verificar record rules y ACL Justech en PROD | P0 | ⏳ |
| C4 | Configurar alias mail (`catchall`, `bounce`, `default.from`) | P1 | ⏳ |
| C5 | Revisar crons activos post-neutralización | P1 | ⏳ |
| C6 | Plan de rollback documentado | P0 | Ver [ROLLBACK.md](ROLLBACK.md) |

### Fase D — Corte y comunicación

| # | Item | Prioridad | Estado |
|---|------|-----------|--------|
| D1 | Ventana de mantenimiento acordada | P0 | ⏳ |
| D2 | Comunicación a usuarios finales | P1 | ⏳ |
| D3 | Decisión sobre destino de `odoo-pecv` post-corte | P1 | ⏳ |
| D4 | Smoke test post Go-Live (login, factura, NCF, reporte DGII) | P0 | ⏳ |

---

## 5. Configuración Traefik objetivo (referencia)

Cuando exista el stack `hellenia-prod`, añadir al servicio Odoo:

```yaml
labels:
  - traefik.enable=true
  - traefik.http.routers.hellenia-prod.rule=Host(`odoo.hellenia.cloud`)
  - traefik.http.routers.hellenia-prod.entrypoints=websecure
  - traefik.http.routers.hellenia-prod.tls.certresolver=letsencrypt
  - traefik.http.services.hellenia-prod.loadbalancer.server.port=8069
```

Parámetros Odoo producción propuestos:

```ini
proxy_mode = True
dbfilter = ^hellenia_prod$
```

```text
ir.config_parameter web.base.url = https://odoo.hellenia.cloud
```

---

## 6. Middleware y endurecimiento post Go-Live

No hay middlewares custom en routers actuales. Sugeridos para producción:

| Middleware | Propósito |
|------------|-----------|
| Rate limiting `/web/login` | Mitigar fuerza bruta |
| HSTS vía Traefik | Forzar HTTPS |
| IP whitelist admin (opcional) | Restringir `/web` administrativo |

---

## 7. Backups actuales (referencia)

| Ambiente | Último backup | Script |
|----------|---------------|--------|
| DEV | `2026-06-30_1210` | `backup-dev.sh` |
| TEST | `2026-06-30_1218` | `backup-test.sh` |
| PROD (`odoo-pecv`) | Fuera de alcance Fase 7.5 | Responsabilidad stack legacy |

---

## 8. Riesgos Go-Live

| ID | Riesgo | Severidad | Mitigación |
|----|--------|-----------|------------|
| GL-01 | `odoo.hellenia.cloud` sin stack | Alta | Desplegar `hellenia-prod` antes de corte |
| GL-02 | Coexistencia Odoo 18 y 19 en mismo VPS | Media | Aislar redes Docker; no compartir BD |
| GL-03 | Licencia Enterprise en dos BDs activas | Alta | Política un código; desregistrar legacy |
| GL-04 | Sin backup `odoo-pecv` antes de cambios | Alta | Backup obligatorio pre-corte |
| GL-05 | Usuarios con permisos excesivos | Media | Implementar [ROLE_MATRIX.md](ROLE_MATRIX.md) |
| GL-06 | Sin SMTP — notificaciones fallan | Media | Configurar antes o inmediatamente post Go-Live |

---

## 9. Preguntas de cierre

| Pregunta | Respuesta Fase 7.5 |
|----------|-------------------|
| ¿DNS preparado? | **Sí** |
| ¿URL lista para Go-Live? | **No** — falta stack + router + certificado + BD |
| ¿Producción movida? | **No** |
| ¿Stack `odoo-pecv` modificado? | **No** |
| ¿Acción requerida ahora? | Esperar UAT + aprobación; planificar Fase Go-Live |

---

## 10. Referencias

- [PRODUCTION_URL_READINESS.md](PRODUCTION_URL_READINESS.md)
- [PRODUCTION_INFRASTRUCTURE_CHECKLIST.md](PRODUCTION_INFRASTRUCTURE_CHECKLIST.md)
- [SECURITY_AUDIT.md](SECURITY_AUDIT.md)
- [ROLE_MATRIX.md](ROLE_MATRIX.md)
- [SYSTEM_CONFIGURATION.md](SYSTEM_CONFIGURATION.md)
- [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md)
- [PHASE75_CERTIFICATION.md](PHASE75_CERTIFICATION.md)
