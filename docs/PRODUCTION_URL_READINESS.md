# Preparación URL producción — odoo.hellenia.cloud

**Fecha:** 2026-06-30  
**Estado:** **DNS LISTO — ROUTER PENDIENTE**  
**Producción operativa actual:** no movida

---

## 1. Objetivo

Preparar la infraestructura para que la URL definitiva de producción sea:

**https://odoo.hellenia.cloud**

Sin ejecutar Go-Live ni modificar el stack `odoo-pecv` (Odoo 18 en producción legacy).

---

## 2. Verificaciones realizadas

### 2.1 DNS

```text
$ dig +short odoo.hellenia.cloud A
2.25.69.179
```

✅ El registro apunta al VPS Hellenia (`srv.hellenia.cloud`).

### 2.2 Traefik

| Verificación | Resultado |
|--------------|-----------|
| Contenedor `traefik-traefik-1` | ✅ Up |
| Entrypoints `web` / `websecure` | ✅ Configurados |
| Redirect HTTP → HTTPS | ✅ Global |
| ACME Let's Encrypt | ✅ `certificatesresolvers.letsencrypt` |
| Router `odoo.hellenia.cloud` | ❌ **No existe** |

Routers activos con Odoo:

| Router | Host |
|--------|------|
| `hellenia-dev` | `dev.hellenia.cloud` |
| `hellenia-test` | `test.hellenia.cloud` |
| `odoo-pecv` | `odoo-pecv.srv1784296.hstgr.cloud` |

### 2.3 HTTPS / certificado

| Prueba | Resultado |
|--------|-----------|
| `curl https://odoo.hellenia.cloud/` | HTTP **404** |
| Certificado TLS | **TRAEFIK DEFAULT CERT** (autofirmado) |
| SNI `odoo.hellenia.cloud` | Sin certificado Let's Encrypt emitido |

**Causa:** Traefik recibe tráfico en `:443` para ese Host, pero ningún servicio Odoo declara router para `odoo.hellenia.cloud`. Responde con certificado por defecto y 404.

### 2.4 Headers y proxy

Configuración objetivo para producción (referencia DEV/TEST):

```ini
# odoo.conf
proxy_mode = True
```

Traefik termina TLS y reenvía a Odoo:8069. Headers `X-Forwarded-*` los gestiona Traefik automáticamente con el provider Docker.

`web.base.url` en producción futura debe ser:

```text
https://odoo.hellenia.cloud
```

---

## 3. Configuración pendiente (Go-Live)

### Opción A — Nuevo stack Odoo 19 (recomendado)

1. Desplegar `hellenia-prod` con imagen Enterprise Odoo 19.
2. Añadir labels Traefik al servicio `odoo`:

```yaml
labels:
  - traefik.enable=true
  - traefik.http.routers.hellenia-prod.rule=Host(`odoo.hellenia.cloud`)
  - traefik.http.routers.hellenia-prod.entrypoints=websecure
  - traefik.http.routers.hellenia-prod.tls.certresolver=letsencrypt
  - traefik.http.services.hellenia-prod.loadbalancer.server.port=8069
```

3. Primera petición HTTPS disparará emisión LE para `odoo.hellenia.cloud`.
4. Establecer `ir.config_parameter` `web.base.url`.

### Opción B — Alias temporal en `odoo-pecv` (no recomendado)

Añadir regla Host adicional al stack Odoo 18 legacy. **No ejecutado** — implicaría tocar producción y mantener Odoo 18 como destino del dominio definitivo.

---

## 4. Middleware

No hay middlewares custom en routers actuales (auth, rate-limit, etc.). Configuración mínima estándar Traefik + Odoo `proxy_mode=True`.

Middleware futuros sugeridos (post Go-Live):

- Rate limiting en `/web/login`
- Headers seguridad (`HSTS` vía Traefik)
- IP whitelist admin (opcional)

---

## 5. Comparativa ambientes

| URL | HTTP login | TLS LE | `web.base.url` |
|-----|------------|--------|----------------|
| https://dev.hellenia.cloud | 200 | ✅ | `https://dev.hellenia.cloud` |
| https://test.hellenia.cloud | 200 | ✅ | `https://test.hellenia.cloud` |
| https://odoo.hellenia.cloud | 404 | ❌ default | N/A (sin stack) |

---

## 6. Conclusión

| Pregunta | Respuesta |
|----------|-----------|
| ¿DNS preparado? | **Sí** |
| ¿URL lista para Go-Live? | **No** — falta stack + router Traefik + certificado LE |
| ¿Producción movida? | **No** |
| ¿Acción requerida ahora? | Ninguna en `odoo-pecv` — documentar y planificar stack Odoo 19 PROD |

---

## 7. Evidencia

- Verificación DNS/TLS: 2026-06-30 (agente Fase 7)
- Labels Traefik: `docker inspect` en `hellenia-dev-odoo-1`, `hellenia-test-odoo-1`, `odoo-pecv-odoo-1`
- Documento relacionado: [PRODUCTION_INFRASTRUCTURE_CHECKLIST.md](PRODUCTION_INFRASTRUCTURE_CHECKLIST.md)
