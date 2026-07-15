# Resultado de preparación UAT — Fase 2

**Fecha:** 2026-07-15  
**Entorno:** justech_dev  
**Producción:** ABSENT (confirmado)  
**Correos DEMO Credicefi últimas 6h:** 0  
**Facturas nuevas UAT:** 0 (suscripción draft)

## Datos DEMO listos

| Registro | Estado preparación |
|---|---|
| MS-2026-0001 | Completo (Credicefi, contacto, fee 35k, vínculos, L1-L3, Activo) |
| MS-2026-0002 | Iguala histórica sin lev/opp/SO; fee 15k; alcance lleno |
| LEV-2026-0007 | service_created; botones Abrir*; sin duplicar opp/servicio |
| Opp 284 | Ganado |
| C-0003890 | Cotización draft vinculada |
| C-0003891 | Suscripción draft plan Mensual, RD$35,000 + ITBIS |
| Ticket 691 | Credicefi + MS-0001 + Soporte Justech |

## Validaciones técnicas automatizadas

| Prueba | Resultado |
|---|---|
| No duplicar oportunidad | PASS |
| No duplicar servicio | PASS |
| Cotizaciones smart button (LEV) | PASS (1 = C-0003890) |
| Tickets desde MS filtra servicio | PASS ([691]) |
| Crear iguala histórica sin lev/opp | PASS |
| Técnico write fee denegado | PASS |
| Sin permisos sin acceso | PASS |
| Menú Resumen primero | PASS |

## Correcciones Fase 2 aplicadas durante UAT prep (defectos)

1. **Record rules** Comercial/Técnico: visibilidad de servicios de la compañía (antes search=0).
2. **Compute contadores** usa `sudo` en sale/account/helpdesk para no romper formularios a usuarios sin ACL de Ventas.
3. Datos DEMO: contacto principal, responsables Fausto, alcance/fee/historical completados.
4. Precio línea suscripción restaurado a RD$35,000.

## Observaciones / no bloqueantes

- Botones MS en Contacto bajo menú **Más**.
- Cotizaciones en MS-0001 puede mostrar 2 (SO + subscription).
- Push notification toast del navegador.

## Pendientes reales (fuera de este UAT)

- Facturación automática, consumo horas, reportes mensuales, SLA avanzado.
- Mejorar overflow de smart buttons en Contacto (prioridad UI).
- Catálogo productos DEMO propio (hoy reutiliza Servicios de Iguala).

## Capturas

Carpeta `manual-validation/` (01–12 PNG) + PDF LEV-2026-0007.

## Confirmaciones

- No merge.
- No despliegue Producción.
- No facturas confirmadas.
- No correos reales.
