# Auditoría partners duplicados — impacto wizard de pagos

**Fecha:** 2026-07-01  
**Alcance:** PROD `hellenia_prod`, TEST `hellenia_test`

## SMOKE P13.4 CF

### PROD

| partner_id | create_date | facturas posted | pendientes | notas |
|------------|-------------|-----------------|------------|-------|
| 21 | 2026-06-30 | 1 | 0 | Datos prueba fase 13 |
| **22** | 2026-06-30 | 1 | **1** | INV/2026/00002 — **usar este id** |
| 23 | 2026-06-30 | 3 | 0 | Creado en pruebas 19.x; facturas pagadas |

### TEST

| partner_id | pendientes |
|------------|------------|
| **2361** | **3** | Escenario validación Playwright |

## Riesgos

1. **Autocomplete ambiguo** — tres registros con mismo `name`; Odoo devuelve el primero por id (21 o 23 sin pendientes).
2. **Conciliación** — pagos ligados al `partner_id` incorrecto no aplican a facturas del id correcto.
3. **Reportes DGII** — NCF y partner deben ser consistentes por `res.partner.id`.

## Recomendaciones (requieren autorización)

| Acción | ids | Impacto |
|--------|-----|---------|
| **Fusionar** | 21, 23 → 22 | Limpia duplicados; revisar movimientos antes |
| **Archivar** | 21, 23 | Si no tienen movimientos abiertos |
| **Ref obligatorio** | todos | `ref='SMOKE-P134-CF'` solo en id 22 |
| **Wizard** | — | Siempre `default_partner_id` en contexto; nunca buscar por nombre en código |

## Regla wizard (implementada 20.1)

- Dominio facturas: `('partner_id', '=', self.partner_id.id)`
- Sin búsqueda por `name`, `display_name` ni texto libre.
