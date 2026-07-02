# Checklist — Infraestructura producción futura

**URL objetivo:** https://odoo.hellenia.cloud  
**Fecha revisión:** 2026-06-30  
**Alcance:** Preparación y verificación — **sin migrar ni modificar producción actual**

---

## 1. Estado actual vs objetivo

| Componente | Producción actual | Objetivo Go-Live |
|------------|-------------------|------------------|
| Stack | `odoo-pecv` (Odoo 18) | `hellenia-prod` (Odoo 19 Enterprise — futuro) |
| Dominio activo | `odoo-pecv.srv1784296.hstgr.cloud` | `odoo.hellenia.cloud` |
| BD | PostgreSQL en `odoo-pecv-db-1` | Por definir (nueva instancia) |
| Licencia Enterprise | Odoo 18 legacy | Migración código `M260616306091776` en go-live |

**Regla:** No detener ni modificar `odoo-pecv` hasta backup + aprobación explícita.

---

## 2. DNS

| Registro | Valor esperado | Estado 2026-06-30 |
|----------|----------------|-------------------|
| `odoo.hellenia.cloud` A | `2.25.69.179` | ✅ Resuelve correctamente |
| `dev.hellenia.cloud` A | `2.25.69.179` | ✅ |
| `test.hellenia.cloud` A | `2.25.69.179` | ✅ |

---

## 3. Traefik

| Item | DEV | TEST | PROD futura |
|------|-----|------|-------------|
| `traefik.enable` | ✅ | ✅ | ⏳ Pendiente |
| Router Host rule | `dev.hellenia.cloud` | `test.hellenia.cloud` | `odoo.hellenia.cloud` — **no configurado** |
| Entrypoint | `websecure` | `websecure` | `websecure` |
| TLS resolver | `letsencrypt` | `letsencrypt` | `letsencrypt` |
| HTTP → HTTPS redirect | ✅ (global) | ✅ | ✅ |
| Service port | 8069 | 8069 | 8069 |

### Producción actual (`odoo-pecv`)

```
Host(`odoo-pecv.srv1784296.hstgr.cloud`)
```

Ubicación compose: `/docker/odoo-pecv/docker-compose.yml` (fuera del repo hellenia).

---

## 4. Certificados TLS

| Dominio | Emisor | Estado |
|---------|--------|--------|
| `dev.hellenia.cloud` | Let's Encrypt (YR2) | ✅ Válido hasta 2026-09-27 |
| `test.hellenia.cloud` | Let's Encrypt (YR2) | ✅ Válido hasta 2026-09-27 |
| `odoo.hellenia.cloud` | Traefik Default Cert | ⚠️ Sin router LE — certificado autofirmado |

---

## 5. Odoo — parámetros web

| Parámetro | DEV | TEST | PROD futura |
|-----------|-----|------|-------------|
| `web.base.url` | `https://dev.hellenia.cloud` | `https://test.hellenia.cloud` | `https://odoo.hellenia.cloud` |
| `proxy_mode` | `True` | `True` | `True` (requerido) |
| `dbfilter` | `^hellenia_dev$` | `^hellenia_test$` | `^hellenia_prod$` (propuesto) |

---

## 6. Docker / redes

| Stack | Proyecto | Contenedores | Red |
|-------|----------|--------------|-----|
| DEV | `hellenia-dev` | odoo + db | `hellenia-dev_default` |
| TEST | `hellenia-test` | odoo + db | `hellenia-test_default` |
| PROD legacy | `odoo-pecv` | odoo + db | red Docker propia |
| Proxy | `traefik` | traefik | socket Docker provider |

**Sin cambios de infraestructura** en esta fase.

---

## 7. Backups

| Ambiente | Último backup conocido | Script |
|----------|------------------------|--------|
| DEV | Sprint 0 / operación continua | `backup-dev.sh` |
| TEST | `2026-06-30_1218` (pre-promoción MVP) | `backup-test.sh` |
| PROD (`odoo-pecv`) | Responsabilidad stack legacy | Fuera de alcance Fase 7 |

---

## 8. Pendientes antes de Go-Live

| # | Item | Prioridad |
|---|------|-----------|
| 1 | Definir stack Odoo 19 producción (`docker/production/` o evolución imagen Enterprise) | P0 |
| 2 | Añadir router Traefik `Host(\`odoo.hellenia.cloud\`)` al stack producción objetivo | P0 |
| 3 | Emitir certificado Let's Encrypt para `odoo.hellenia.cloud` | P0 |
| 4 | Configurar `web.base.url` producción | P0 |
| 5 | Migrar licencia Enterprise DEV → PROD (política un código / una BD) | P0 |
| 6 | Backup completo `odoo-pecv` antes de cualquier cambio | P0 |
| 7 | Plan de corte DNS / comunicación usuarios | P1 |
| 8 | Monitoreo y logrotate producción | P1 |

---

## 9. Referencias

- [PRODUCTION_URL_READINESS.md](PRODUCTION_URL_READINESS.md)
- [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md)
- [E1B-LICENSE-CHECKLIST.md](E1B-LICENSE-CHECKLIST.md)
- `config/production/README.md` (referencia `odoo-pecv`)
