# Servicios Administrados (Justech)

Módulo Odoo 19 — **Fase 1: Levantamientos** de Servicios Administrados e Igualas.

## Alcance

- Creación y seguimiento de levantamientos desde el backend.
- Formulario público multipágina (16 secciones) con enlace seguro por token.
- Guardado parcial y envío final con aceptación.
- PDF, plantilla de correo e integración con `res.partner` y `crm.lead`.

## Instalación (solo DEV)

```bash
# En erp.justech.do / justech_dev — NO Producción
odoo-bin -d justech_dev -i justech_managed_services --stop-after-init
```

Asignar grupo **Usuario** o **Administrador de Servicios Administrados** a los consultores.

## Rutas públicas

| Método | Ruta |
|--------|------|
| GET | `/servicios/levantamiento/<token>` |
| POST (JSON) | `/servicios/levantamiento/<token>/save` |
| POST (JSON) | `/servicios/levantamiento/<token>/submit` |

## Dependencias

`base`, `mail`, `contacts`, `crm`, `website`, `portal`

## Documentación

- `docs/FUNCIONAL.md` — flujo de negocio.
- `docs/TECNICO.md` — modelos, API pública y esquema `form_data`.
- `docs/SECURITY_CONTRACT.md` — grupos, ACL y reglas.

## Licencia

LGPL-3.0 — ver `LICENSE`.
