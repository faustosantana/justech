# Evidencia — justech_managed_services (fase 1) en justech_dev

## Entorno
- Host: `207.244.242.58` (`erp.justech.do` / odoo-dev)
- Base: **justech_dev**
- Rama: `feature/managed-services-assessment`
- Producción (`31.97.6.178` / `justech`): **no modificada** (módulo ausente, count=0)

## Backup previo
- `/opt/odoo-dev/backups/p0-managed-services-20260715_194056/`
- Dump + filestore + restore test PASS

## Instalación
- Módulo: `justech_managed_services` `19.0.1.0.0` → **installed**
- Path DEV: `/opt/odoo-dev/custom-addons/justgroup/custom_addons/justech_managed_services`

## UAT (shell + HTTP)
- Ver `uat_managed_services_20260715_195555.txt` (39/40 luego corregido submitted_token → PASS)
- Validado: secuencia LEV-2026-####, token, URL pública, guardado parcial, envío, reopen, cancel,
  CRM sin duplicar, PDF (~21KB), smart buttons, ACL bare user, HTTP 200 form + invalid corporate page

## Rutas públicas
- `GET /servicios/levantamiento/<token>`
- `POST /servicios/levantamiento/<token>/save` (jsonrpc)
- `POST /servicios/levantamiento/<token>/submit` (jsonrpc)

## Seguridad
- Grupos: `group_ms_user`, `group_ms_manager` (privilege Odoo 19)
- Record rules: usuario asignado / manager / multi-company
- ACL: user sin unlink; manager con unlink

## Capturas HTML
- `screenshots/form_public.html` (token redactado)
- `screenshots/invalid_token.html`

## Riesgos / pendientes
- Desinstalación completa no re-ejecutada al final (evitar downtime; install limpia validada)
- Screenshots PNG/móvil pendientes de captura manual en browser si se requieren visualmente
- Retenciones / fase 2 (igualas, fees, helpdesk): no implementadas (por diseño)
- Correos reales: no enviados (SMTP sink DEV)

## Próxima fase (autorización separada)
- Iguala / catálogo servicios / SLA / fee mensual vía facturación estándar Odoo
