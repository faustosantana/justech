# Auditoría Configuración Sistema — Fase 8

**Ambiente:** DEV únicamente  
**Fecha:** 2026-06-30  
**Estado bloque:** **PASS CON OBSERVACIONES**

---

## 1. SMTP y correo

| Item | DEV | Estado |
|------|-----|--------|
| Servidores salientes (`ir.mail_server`) | 0 | ⚠️ Pendiente |
| `mail.default.from` | No configurado | ⚠️ |
| `mail.catchall.domain` | No configurado | ⚠️ |
| `mail.bounce.alias` | No configurado | ⚠️ |
| `mail.catchall.alias` | No configurado | ⚠️ |

**Impacto UAT:** notificaciones por correo no funcionarán hasta configurar SMTP.

**Propuesta:** Microsoft 365 o Google Workspace con `noreply@helleniadr.com`.

---

## 2. Plantillas de correo

Plantillas estándar Odoo activas (ventas, compras, facturas). Sin personalización Hellenia aún.

**Pendiente:** branding en plantillas (logo, pie).

---

## 3. Acciones programadas (cron)

| Ambiente | Activos | Inactivos |
|----------|---------|-----------|
| DEV | 29 | 5 |

### Crons críticos

| Cron | Intervalo | Riesgo |
|------|-----------|--------|
| Mail: Email Queue Manager | 1 h | ⚠️ Sin SMTP |
| Account auto-post | 1 día | Bajo |
| Publisher warranty check | 1 semana | Bajo |
| Digest Emails | 1 día | Bajo |

---

## 4. Logs

| Fuente | Ubicación | Nivel |
|--------|-----------|-------|
| Odoo DEV | Docker stdout | `debug` |
| Scripts deploy | `logs/deploy/` | texto |
| Traefik | contenedor | INFO |

Sin errores CRITICAL al cierre Fase 8.

---

## 5. Backups

| Backup | Ruta | Verificado |
|--------|------|------------|
| Pre-Fase 8 | `backups/dev/2026-06-30_1400` | ✅ |
| Retención | 7d / 4s / 6m | ✅ |

Scripts: `backup-dev.sh`, `verify-backup-dev.sh`

---

## 6. Parámetros sistema

| Clave | Valor DEV |
|-------|-----------|
| `web.base.url` | `https://dev.hellenia.cloud` |
| `database.enterprise_code` | Registrado |
| `proxy_mode` | `True` (odoo.conf) |

---

## 7. Usuarios

| Login | Activo | Rol |
|-------|--------|-----|
| `admin` | Sí | Emergencia |
| `it@justech.do` | Sí | Admin TI |

**Usuarios funcionales:** 0 (por diseño Fase 8).

---

## 8. Infraestructura (solo documentación)

| Componente | DEV | PROD futura |
|------------|-----|-------------|
| DNS | `dev.hellenia.cloud` → 2.25.69.179 | `odoo.hellenia.cloud` DNS listo |
| Traefik router | ✅ | ❌ Pendiente |
| TLS Let's Encrypt | ✅ | ❌ Pendiente |
| Stack | `hellenia-dev` | `hellenia-prod` pendiente |

**TEST y PRODUCCIÓN no modificados en Fase 8.**

Ver [GO_LIVE_READINESS.md](GO_LIVE_READINESS.md).

---

## 9. Integraciones

| Integración | Estado |
|-------------|--------|
| Pasarela pago (link/tarjetas) | Estructura manual — sin gateway |
| e-CF / Infile | Futuro |
| POS | No instalado |
| Barcode app | Desinstalado |

---

## 10. Validación

| Check | Resultado |
|-------|-----------|
| Crons | ✅ |
| Usuarios controlados | ✅ |
| `web.base.url` | ✅ |
| SMTP | ⚠️ Pendiente |

```
Estado: PASS CON OBSERVACIONES
Causa: SMTP y alias correo pendientes
Impacto: UAT con correo limitado
Prioridad: P1 SMTP antes de escenarios notificación
Propuesta: configurar SMTP en DEV para UAT; replicar en TEST al promover
```

---

## 11. Referencias

- [SYSTEM_CONFIGURATION.md](SYSTEM_CONFIGURATION.md) (Fase 7.5)
- [SECURITY_AUDIT.md](SECURITY_AUDIT.md)
- [ADMINISTRATOR_GUIDE.md](ADMINISTRATOR_GUIDE.md)
