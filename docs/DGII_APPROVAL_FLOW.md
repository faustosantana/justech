# Flujo de aprobación exclusiones DGII

## Estados del reporte

| Estado | Descripción |
|--------|-------------|
| Borrador | Recién creado, líneas no cargadas |
| Validado | Período validado, sin exclusiones manuales pendientes |
| Requiere aprobación | Hay exclusiones manuales sin aprobar |
| Aprobado | Supervisor aprobó exclusiones |
| Rechazado | Supervisor rechazó — documentos re-incluidos |
| Generado | Excel DGII exportado con hash registrado |

## Reglas

- Sin exclusiones manuales: Validado → Generado (supervisor).
- Con exclusiones manuales: Validado → Requiere aprobación → Aprobado → Generado.

## Permisos

| Rol | Acciones |
|-----|----------|
| Usuario fiscal (`group_justech_do_fiscal_user`) | Cargar, validar, excluir con motivo, descargar errores |
| Supervisor (`group_justech_do_fiscal_manager`) | Aprobar, rechazar, generar Excel, reabrir |

## Notificaciones

Al enviar a aprobación: mensaje en chatter del reporte + actividad To Do para supervisores (sin email externo).
