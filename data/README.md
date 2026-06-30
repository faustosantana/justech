# Datos iniciales transversales (no pertenecen a un módulo)

Este directorio almacena **datos de referencia** que no encajan en un módulo custom específico:

- Catálogos maestros compartidos entre ambientes
- XML/CSV de carga inicial one-shot
- Plantillas de importación

## Separación de responsabilidades

| Capa | Ubicación | Ejemplo |
|------|-----------|---------|
| **Infraestructura** | `docker/` | Compose, imágenes |
| **Configuración** | `config/` | `odoo.conf`, `.env` |
| **Datos iniciales** | `data/` | CSV maestros globales |
| **Datos por módulo** | `custom/<modulo>/data/` | XML del módulo |
| **Módulos** | `custom/` | Lógica de negocio |
| **Scripts** | `scripts/` | Automatización |
| **Documentación** | `docs/` | Guías y políticas |

## Uso

Los archivos aquí **no se cargan automáticamente** en Odoo. Los scripts de despliegue o módulos custom los referencian cuando corresponda.

## Reglas

- No almacenar secretos ni credenciales
- Versionar solo datos no sensibles
- Preferir `custom/<modulo>/data/` para datos acoplados a un módulo
