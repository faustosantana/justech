# Justech Security UX — Permisos Operativos

Capa de administración amigable de permisos sobre `res.groups`.

## Qué hace

- Muestra checkboxes operativos organizados por módulo en la ficha del usuario.
- Activa/desactiva los grupos reales de Odoo correspondientes.
- Refleja el estado real si los grupos cambian en Avanzado.

## Qué no hace

- No crea una segunda capa de ACL.
- No modifica `ir.model.access` ni `ir.rule`.
- No altera `implied_ids` ni migra usuarios.

## Fuente de verdad

`res.groups` (y sus implicaciones).
