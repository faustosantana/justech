# Documentación funcional — Servicios Administrados (Fase 1)

## Objetivo

Permitir a Justech levantar información estructurada del entorno tecnológico de un cliente o prospecto mediante un formulario público seguro, sin login, con seguimiento interno en Odoo.

## Flujo

1. El consultor crea un **Levantamiento** y selecciona cliente/prospecto.
2. Genera un **enlace público** (token) y opcionalmente lo envía por correo.
3. El cliente completa el formulario (guardar parcial o envío final).
4. El consultor revisa respuestas, genera PDF y puede crear una **oportunidad CRM**.

## Estados

| Estado | Descripción |
|--------|-------------|
| Borrador | Recién creado, sin enlace activo |
| Enviado | Enlace generado / correo enviado |
| En proceso | Cliente guardó avance |
| Completado | Cliente envió el formulario |
| Revisado | Revisión interna finalizada |
| Propuesta preparada | Listo para siguiente fase comercial |
| Cancelado | Levantamiento anulado |

## Menú

**Servicios Administrados → Levantamientos**

## Integraciones

- **Contactos:** smart button *Levantamientos* con contador.
- **CRM:** vínculo opcional con `crm.lead`; creación manual desde botón; origen UTM *Levantamiento de Servicios Administrados*.

## Formulario público

- 16 secciones según especificación de negocio.
- Pantalla de revisión, aceptación y confirmación final.
- Páginas de error corporativas para enlaces inválidos, vencidos, inactivos o cancelados.

## Permisos

- **Usuario:** CRUD sobre levantamientos asignados (consultor o creador); sin eliminar completados.
- **Administrador:** acceso total; puede reabrir formularios y eliminar con validación.

## Fuera de alcance (fases futuras)

Contratos, igualas, fees mensuales, helpdesk, SLA operativo, facturación recurrente y portal completo del cliente.
