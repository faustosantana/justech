# RETENCIONES-1 — Matriz de Riesgos

| # | Riesgo | Prob. | Impacto | Mitigación | Estado |
|---|---|---|---|---|---|
| R1 | Romper el motor de retenciones de Hellenia en PROD | Baja | Alto | Etapa A no toca `hellenia_account`; motor intacto | Mitigado |
| R2 | Romper la dependencia 623 (`justech_l10n_do_reports`→`hellenia_account`) | Baja | Alto | Etapa A no cambia la dependencia; Etapa B la repunta en PR aislado | Mitigado |
| R3 | Cambiar/duplicar XML IDs o campos | Baja | Alto | Etapa A no crea campos ni toca XML IDs; Etapa B usa re-parenting `ir.model.data` | Mitigado |
| R4 | Romper el catálogo de licencias existente | Baja | Medio | Se **añade** al whitelist (no se reemplaza); 6 items previos intactos (validado en TEST) | Mitigado |
| R5 | La personalización aparece sin el módulo técnico | Baja | Medio | `technical_modules_all` obliga a que el módulo esté instalado | Mitigado |
| R6 | Tocar impuestos/NCF/DGII/COA/secuencias | — | Alto | El módulo no define ni modifica impuestos, NCF, COA ni secuencias | Evitado |
| R7 | Persistir datos de prueba en TEST | Baja | Bajo | Flujos E2E en transacción con `rollback`; healthcheck con `rollback` | Mitigado |
| R8 | Duplicados en el catálogo de retenciones (1 032 registros, mayoría `RET-NONE` archivados) | Media | Bajo | Higiene de datos pendiente; **no** se toca en esta fase (fuera de alcance) | Abierto (no bloqueante) |
| R9 | No hay retenciones activas en la compañía de TEST | Media | Bajo | El motor funciona al activarlas (`sync_catalog_from_taxes`); verificado E2E activando RET-ITBIS-30 en transacción | Informativo |
| R10 | Etapa B (reubicación física) sin backup en PROD | Media | Alto | Backup obligatorio + validación TEST PR-a-PR antes de PROD | Controlado por plan |

## Conclusión de riesgo
La **Etapa A es de bajo riesgo y reversible**. La **Etapa B** (reubicación física) concentra el
riesgo real y solo debe ejecutarse con aprobación, PRs pequeños, backup y validación previa en TEST.
