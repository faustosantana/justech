# Configuración SMTP — Hellenia

**Fase:** 12  
**Estado:** **FAIL en DEV** — TEST neutralizado puede mostrar servidor dummy

---

## 1. Estado por ambiente

| Ambiente | Servidores `ir.mail_server` | Envío real |
|----------|----------------------------|------------|
| DEV | 0 | ❌ |
| TEST | 1 (neutralizado) | ❌ bloqueado |
| PROD | 0 | ❌ no desplegado |

---

## 2. Entregable requerido (Cliente)

| Parámetro | Ejemplo |
|-----------|---------|
| Servidor SMTP | `smtp.office365.com` o proveedor |
| Puerto | 587 (STARTTLS) o 465 (SSL) |
| Usuario | `noreply@helleniadr.com` |
| Contraseña | *(secreto — no en repo)* |
| From por defecto | `noreply@helleniadr.com` |
| Dominio catchall | `helleniadr.com` |

---

## 3. Parámetros Odoo a configurar (Go-Live)

| Clave | Valor sugerido |
|-------|----------------|
| `mail.default.from` | `noreply@helleniadr.com` |
| `mail.catchall.domain` | `helleniadr.com` |
| `mail.bounce.alias` | `bounce` |
| `mail.catchall.alias` | `catchall` |

**Ubicación:** Ajustes → Técnico → Correo → Servidores de correo saliente

---

## 4. Validaciones post-configuración

| Prueba | Criterio |
|--------|----------|
| Envío prueba | Correo recibido en bandeja externa |
| Recuperación contraseña | Email llega al usuario |
| Notificación factura | PDF adjunto (opcional) |
| Factura PDF | Logo + NCF visible |

---

## 5. Procedimiento Justech (sin ejecutar en Fase 12)

1. Crear `ir.mail_server` en `hellenia_prod`
2. Configurar parámetros sistema
3. Enviar correo prueba desde Ajustes
4. Documentar en acta Go-Live

**Seguridad:** credenciales solo en `config/production/.env` o gestor secretos — nunca en git.

---

## 6. Certificación Fase 12

| Criterio | Estado |
|----------|--------|
| Documentación procedimiento | **PASS** |
| SMTP operativo | **FAIL** |
| Notificaciones validadas | **FAIL** |
