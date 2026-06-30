# Guía del administrador — Hellenia Odoo 19

**Versión:** 1.0 (Fase 7.5)  
**Fecha:** 2026-06-30  
**Audiencia:** Administrador TI Justech (`it@justech.do`) y personal autorizado Hellenia

---

## 1. Cuentas administrativas

### 1.1 Cuenta operativa — Justech IT

| Campo | Valor |
|-------|-------|
| Login | `it@justech.do` |
| Nombre | Justech IT |
| Correo | `it@justech.do` |
| Idioma | `es_DO` |
| Zona horaria | `America/Santo_Domingo` |
| Ambientes | DEV y TEST (PROD pendiente Go-Live) |

**Uso:** Administración diaria, configuración, despliegues, soporte técnico.

**Grupos asignados:**

| Grupo efectivo | XML ID |
|----------------|--------|
| Access Rights (Settings) | `base.group_system` |
| Role / Administrator | `base.group_erp_manager` |
| Accounting / Administrator | `account.group_account_manager` |
| Sales / Administrator | `sales_team.group_sale_manager` |
| Purchase / Administrator | `purchase.group_purchase_manager` |
| Inventory / Administrator | `stock.group_stock_manager` |
| Technical Features | `base.group_no_one` |
| Dominican Fiscal Manager | `justech_l10n_do_base.group_justech_do_fiscal_manager` |

La contraseña se entrega por canal seguro. **No está documentada en este repositorio.**

### 1.2 Cuenta de recuperación — `admin`

| Campo | Valor |
|-------|-------|
| Login | `admin` |
| Propósito | **Solo emergencia** — recuperación de acceso si `it@justech.do` queda bloqueado |
| Estado | Activo en DEV y TEST |

**Política:**

- No usar `admin` para operación diaria.
- Documentar cada uso de `admin` (fecha, motivo, acciones).
- Post Go-Live: considerar desactivar o restringir contraseña en caja fuerte.

---

## 2. URLs y bases de datos

| Ambiente | URL | Base de datos | Neutralizado |
|----------|-----|---------------|--------------|
| DEV | https://dev.hellenia.cloud | `hellenia_dev` | No |
| TEST | https://test.hellenia.cloud | `hellenia_test` | Sí |
| PROD futura | https://odoo.hellenia.cloud | Por definir | N/A |

**VPS:** `2.25.69.179` (`srv.hellenia.cloud`)  
**Ruta proyecto:** `/opt/odoo-projects/hellenia`

---

## 3. Scripts de administración

Todos los scripts se ejecutan desde la raíz del proyecto en el VPS.

### 3.1 Crear o actualizar usuario técnico

```bash
export JUSTECH_IT_PASSWORD='<contraseña-segura>'
./scripts/create-justech-it-user.sh dev
./scripts/create-justech-it-user.sh test
```

Requiere variable de entorno `JUSTECH_IT_PASSWORD`. El script es idempotente: crea o actualiza grupos, idioma y zona horaria.

### 3.2 Auditoría de seguridad (Fase 7.5)

```bash
./scripts/audit-security-phase75.sh dev
./scripts/audit-security-phase75.sh test
```

Genera:

- `evidence/security-audit-dev.json`
- `evidence/security-audit-test.json`

Incluye: usuarios, grupos, ACL, record rules, crons, SMTP, parámetros.

### 3.3 Auditoría de usuarios

```bash
./scripts/audit-users.sh dev
./scripts/audit-users.sh test
```

### 3.4 Backups

```bash
./scripts/backup-dev.sh
./scripts/backup-test.sh
./scripts/verify-backup-dev.sh
```

Retención configurada: 7 días diarios / 4 semanales / 6 mensuales.

### 3.5 Validación MVP

```bash
./scripts/validate-phase6-mvp.sh dev
./scripts/validate-phase6-mvp.sh test
./scripts/upgrade-phase6-mvp-module.sh dev
```

### 3.6 Configuración empresa

```bash
# Vía odoo shell en contenedor
./scripts/audit-company-config.py
```

---

## 4. Gestión de usuarios funcionales (post-UAT)

**Estado Fase 7.5:** Los usuarios de negocio **no están creados**. La matriz oficial está en [ROLE_MATRIX.md](ROLE_MATRIX.md).

### Procedimiento recomendado al crear usuarios

1. Obtener aprobación escrita de Hellenia con rol asignado.
2. Crear usuario con login corporativo (`nombre.apellido@helleniadr.com`).
3. Asignar **solo** los grupos de la matriz para ese rol.
4. Configurar `es_DO` y `America/Santo_Domingo`.
5. Enviar invitación / contraseña temporal por canal seguro.
6. Registrar en inventario de accesos.
7. Re-ejecutar `audit-security-phase75.sh` y archivar evidencia.

### Roles definidos (sin usuarios aún)

1. Gerencia General  
2. Contabilidad  
3. Caja  
4. Compras  
5. Ventas  
6. Inventario  
7. Atención al cliente  
8. Administrador TI (ya implementado)

---

## 5. Seguridad fiscal Justech

### Grupos fiscales

| Grupo | XML ID | Capacidades |
|-------|--------|-------------|
| Fiscal User | `justech_l10n_do_base.group_justech_do_fiscal_user` | Consultar tipos NCF, consumir, generar reportes |
| Fiscal Manager | `justech_l10n_do_base.group_justech_do_fiscal_manager` | Todo lo anterior + rangos, void NCF, configuración |

**Regla:** Solo Contabilidad (manager) y Administrador TI deben tener Fiscal Manager.

### Controles Sprint 0 activos

- Record rules multiempresa en modelos Justech (6 reglas).
- `action_void_ncf` restringido a Fiscal Manager en servidor.
- Índice único PostgreSQL: `account_move_justech_do_ncf_company_uniq`.
- Lock transaccional en consumo NCF (`pg_advisory_xact_lock`).

---

## 6. Correo / SMTP

**Estado actual:** Sin servidor saliente configurado en DEV; TEST neutralizado.

### Configuración pendiente (antes de UAT con notificaciones)

1. **Ajustes → Técnico → Correo electrónico → Servidores de correo saliente**
   - Servidor SMTP corporativo (Microsoft 365, Google Workspace, etc.)
   - TLS/STARTTLS según proveedor
   - Usuario y contraseña de aplicación

2. **Parámetros del sistema** (`ir.config_parameter`):

| Clave | Valor sugerido |
|-------|----------------|
| `mail.default.from` | `noreply@helleniadr.com` |
| `mail.catchall.domain` | `helleniadr.com` |
| `mail.catchall.alias` | `catchall` |
| `mail.bounce.alias` | `bounce` |

3. Probar envío desde **Ajustes → Correo electrónico → Probar conexión**.

**Advertencia DEV:** Sin SMTP, el cron "Mail: Email Queue Manager" acumula correos en cola sin salida real. No usar correos de clientes reales en DEV.

---

## 7. Scheduled Actions (cron)

| Ambiente | Crons activos | Notas |
|----------|---------------|-------|
| DEV | 29 | Correo activo — riesgo sin SMTP |
| TEST | Similar | Neutralizado — envíos deshabilitados |

### Crons a revisar antes de Go-Live

| Cron | Acción |
|------|--------|
| Mail: Email Queue Manager | Verificar SMTP antes de activar envíos reales |
| Publisher warranty check | Normal — verifica suscripción Enterprise |
| Account auto-post | Revisar política de contabilidad Hellenia |
| Digest Emails | Configurar destinatarios |

Listado completo en evidencia JSON de auditoría.

---

## 8. Multiempresa

**Estado:** Una sola compañía (`Hellenia, S.R.L.`, RNC `133621282`).

Las record rules Justech y estándar Odoo están preparadas para múltiples compañías (`company_id in company_ids`). No activar multiempresa sin plan de segregación de datos y roles.

---

## 9. Despliegues y actualizaciones

### Flujo estándar DEV → TEST

1. Backup ambiente destino.
2. Merge / pull rama `feature/justech-l10n-do-mvp`.
3. `./scripts/deploy-dev.sh` o `./scripts/deploy-test.sh`.
4. `./scripts/upgrade-phase6-mvp-module.sh <env>`.
5. `./scripts/validate-phase6-mvp.sh <env>`.
6. `./scripts/audit-security-phase75.sh <env>`.
7. Documentar en reporte de promoción.

### Reglas

- No desplegar a producción sin UAT firmado.
- No instalar POS hasta fase explícita.
- No cargar datos reales de clientes en DEV.

---

## 10. Logs y diagnóstico

| Fuente | Ubicación |
|--------|-----------|
| Odoo DEV | `docker logs hellenia-dev-odoo-1` |
| Odoo TEST | `docker logs hellenia-test-odoo-1` |
| Traefik | `docker logs traefik-traefik-1` |
| Scripts deploy | `logs/deploy/` |

Nivel log DEV: `debug`. TEST: `info`.

---

## 11. Contactos y escalación

| Rol | Contacto |
|-----|----------|
| Administrador TI Justech | `it@justech.do` |
| Empresa Hellenia | `info@helleniadr.com` |
| Repositorio | https://github.com/faustosantana/justech |
| PR activo | https://github.com/faustosantana/justech/pull/2 |

---

## 12. Documentación relacionada

| Documento | Contenido |
|-----------|-----------|
| [SECURITY_AUDIT.md](SECURITY_AUDIT.md) | Auditoría grupos, ACL, rules |
| [ROLE_MATRIX.md](ROLE_MATRIX.md) | Matriz oficial de roles |
| [SYSTEM_CONFIGURATION.md](SYSTEM_CONFIGURATION.md) | Parámetros sistema |
| [GO_LIVE_READINESS.md](GO_LIVE_READINESS.md) | Checklist producción |
| [UAT_ENVIRONMENT_PREPARATION.md](UAT_ENVIRONMENT_PREPARATION.md) | Preparación UAT |
| [DEVOPS_GUIDE.md](DEVOPS_GUIDE.md) | Operaciones VPS |
| [ROLLBACK.md](ROLLBACK.md) | Procedimiento rollback |

---

## 13. Checklist administrador — inicio de sesión

- [ ] Acceder con `it@justech.do` (no `admin`)
- [ ] Verificar URL correcta (DEV vs TEST)
- [ ] Confirmar compañía activa: Hellenia, S.R.L.
- [ ] Revisar notificaciones / cola de correo si hay incidencias
- [ ] Antes de cambios mayores: ejecutar backup
