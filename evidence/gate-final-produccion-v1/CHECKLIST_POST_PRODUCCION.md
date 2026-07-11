# CHECKLIST_POST_PRODUCCION — Justech Fiscal v1.0

Ejecutar en la hora siguiente al deploy en `justgroup.app`.

## Disponibilidad

- [ ] Login 200 / sin OwlError en home
- [ ] Workers activos; sin ERROR críticos en log (últimos 15 min)
- [ ] Centro de Administración Fiscal abre por empresa

## Fiscal

- [ ] Rangos NCF visibles y activos
- [ ] Padrón: status green o plan de importación en curso
- [ ] Feature flags esperados

## Smoke funcional (1 documento real o lab controlado)

- [ ] Venta: borrador→confirmar→facturar→NCF asignado
- [ ] Compra: factura proveedor con NCF→publicar
- [ ] Pago cliente y pago proveedor
- [ ] Generar vista/export 607 y 606 del período actual (aunque esté vacío de líneas nuevas)

## Seguridad

- [ ] Contador accede reportes DGII / Centro (lectura)
- [ ] Ventas/Compras sin AccessError en sus menús
- [ ] Sin fuga multiempresa en prueba rápida

## Correo e jobs

- [ ] Mail Queue Manager según política PROD
- [ ] Cron padrón `nextcall` futuro coherente
- [ ] Sin cola `outgoing` masiva bloqueada

## Cierre

- [ ] Evidencia guardada (logs, capturas, IDs de smoke)
- [ ] Sponsor informado: GO operativo o ROLLBACK
