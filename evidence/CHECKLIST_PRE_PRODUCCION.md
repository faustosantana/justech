# CHECKLIST_PRE_PRODUCCION — Justech Fiscal v1.0

## Aprobaciones

- [ ] Aprobación **explícita** del propietario para tocar `justgroup.app`
- [ ] Ventana de mantenimiento comunicada a Ventas/Compras/Contabilidad
- [ ] Plan de rollback leído y backup restaurable verificado

## Código y versión

- [ ] Rama release alineada a `feature/fiscal-standard-consolidation` certificada
- [ ] Versiones SemVer módulos Justech documentadas
- [ ] Sin cambios pendientes no auditados en release

## Backup PROD

- [ ] Dump BD completo (`-Fc`)
- [ ] Filestore completo
- [ ] `pg_restore -l` OK / tamaño filestore >= umbral
- [ ] Ruta backup registrada

## Datos fiscales PROD (solo lectura previa)

- [ ] Tipos de comprobante
- [ ] Rangos NCF por empresa / vigentes
- [ ] Padrón cargado o plan de importación listo
- [ ] Dual-write / FDP / Adel freeze según política

## Seguridad

- [ ] Matriz roles: Admin Fiscal, Responsable, Usuario, Contador (+ grupo fiscal), Ventas, Compras
- [ ] Contador con acceso DGII (Responsable Fiscal o equivalente)
- [ ] Feature flags revisados
- [ ] Multiempresa: empresas productivas correctas

## Infraestructura

- [ ] SMTP PROD validado (prueba a buzón controlado)
- [ ] Cron padrón DGII activo + `run_hour`
- [ ] Cron secuencias fiscales / currency / mail queue según política PROD
- [ ] Monitoreo disco/memoria/workers
- [ ] Correos DEV no apuntan a PROD

## Go / No-Go

- [ ] GO solo si todos los ítems críticos anteriores están marcados
