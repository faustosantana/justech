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

## Cierre UAT manual (2026-07-15)

Ver:

- `MANUAL_UAT.md`
- `RESPONSIVE_UAT.md`
- `UNINSTALL_REINSTALL_UAT.md`
- `PERMISSIONS_UAT.md`
- `screenshots/*.png` + `08_pdf_levantamiento.pdf`

Backup UAT: `/opt/odoo-dev/backups/p0-ms-uat-manual-20260715_201527`  
Versión tras fix JS revisión: **19.0.1.0.1**  
Producción: **ABSENT / no tocada**

## Remediación pre-producción (2026-07-15)

Ver:

- `PREPROD_REMEDIATION.md`
- `PDF_FIELD_MATRIX.md` (16/16 PASS)
- `screenshots/11_pdf_preprod_completo.pdf`
- `screenshots/12_resumen_etiquetas_legibles.png`
- `screenshots/13_porcentaje_dinamico.png`

Backup remediación: `/opt/odoo-dev/backups/p0-ms-preprod-remediation-20260715_192515`  
Versión: **19.0.1.0.2**  
Producción: **ABSENT / no tocada**

## Riesgos / pendientes
- Mojibake posible de acentos en PDF según motor wkhtmltopdf DEV (contenido/labels correctos)
- Usuario solo-MS vs ACL fiscal al abrir Contactos/CRM (documentado; no se elevaron grupos)
- Retenciones / fase 2: no implementadas (por diseño)
- Correos reales: no enviados (SMTP sink DEV)

## Próxima fase (autorización separada)
- Iguala / catálogo servicios / SLA / fee mensual vía facturación estándar Odoo
