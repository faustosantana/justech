# Checklist de promoción a PROD — Fase 24.1

> **NO EJECUTAR** hasta aprobación visual explícita y autorización del responsable.  
> Este documento es solo preparación.

---

## Pre-requisitos (bloqueantes)

- [ ] Aprobación visual del diseño PDF firmada (Fausto / responsable)
- [ ] Comparación 1:1 contra HTML/CSS aprobado — sin desviaciones no autorizadas
- [ ] Validación TEST `validation.json` con `"pass": true` en fecha reciente
- [ ] Confirmación explícita: **sí promover a PROD** (comunicación escrita)
- [ ] Ventana de mantenimiento acordada (si aplica)
- [ ] Backup de base de datos PROD realizado y verificado

---

## Preparación del despliegue

- [ ] Merge de rama `cursor/phase24-1-report-design-dd85` a rama de release acordada
- [ ] Revisar diff: solo `custom/justech_report_design/` y documentación relacionada
- [ ] Confirmar que **no** hay cambios en `hellenia_reports` de cotización en el merge
- [ ] Confirmar que **no** hay override de `sale.report_saleorder_document`
- [ ] Tag o release note con versión `19.0.1.0.0` del módulo

---

## Despliegue en PROD (VPS)

- [ ] Copiar `custom/justech_report_design/` al entorno PROD (no TEST)
- [ ] **NO** copiar `evidence/`, scripts de test ni configuración TEST
- [ ] Verificar `addons_path` incluye `/mnt/custom` o ruta equivalente PROD
- [ ] Instalar módulo en base PROD:
  ```bash
  # Ejemplo — ajustar rutas/vars según config/prod/.env
  docker compose --env-file config/prod/.env run --rm -T odoo odoo \
    -d <PROD_DB> -i justech_report_design --stop-after-init --no-http
  ```
- [ ] Reiniciar contenedor Odoo PROD
- [ ] Limpiar cache de assets si los estilos no cargan:
  - Reinicio Odoo + regenerar PDF de prueba

---

## Validación post-despliegue PROD

- [ ] Módulo `justech_report_design` en estado **Instalado** (PROD)
- [ ] Menú Imprimir muestra **Cotización Hellenia (Diseño)**
- [ ] Reporte estándar **Cotización en PDF** sigue funcionando
- [ ] Generar PDF con cotización real (1 producto) — diseño correcto
- [ ] Generar PDF con cotización real (5+ productos) — paginación OK
- [ ] Logo dimensionado correctamente (max 300×95 px)
- [ ] Sin errores QWeb en logs
- [ ] Sin regresión en facturas, pagos, retenciones, DGII
- [ ] Sin regresión en reportes de compra e inventario

---

## Rollback (si falla)

- [ ] Desinstalar módulo en PROD: `-u` no aplica; usar desinstalar desde UI o:
  ```bash
  # Desde odoo shell PROD
  env['ir.module.module'].search([('name','=','justech_report_design')]).button_immediate_uninstall()
  ```
- [ ] Reiniciar Odoo PROD
- [ ] Verificar que reporte estándar de cotización funciona
- [ ] Restaurar backup si hubo impacto en datos (no debería — módulo solo reporte)

---

## Pendientes opcionales post-PROD

- [ ] Exponer reporte paralelo en portal (token / ruta pública)
- [ ] Decidir si reemplazar reporte estándar como default
- [ ] Capacitar usuarios: cuándo usar **Cotización Hellenia (Diseño)** vs estándar
- [ ] Monitoreo 48h post-despliegue (logs, tickets de soporte)

---

## Registro de promoción (completar al ejecutar)

| Campo | Valor |
|-------|-------|
| Fecha promoción | _pendiente_ |
| Ejecutado por | _pendiente_ |
| Base PROD | _pendiente_ |
| Versión módulo | 19.0.1.0.0 |
| Aprobado por | _pendiente_ |
| Ticket / referencia | _pendiente_ |
| Rollback necesario | _pendiente_ |

---

**Estado actual:** ⛔ BLOQUEADO — permanece solo en TEST.
