# Fase 27 — Tipo comprobante fiscal predeterminado en contactos

## Resultado: PASS (TEST + PROD)

| Entorno | Módulos | Validación |
|---------|---------|------------|
| TEST | base 19.0.1.4.0, ncf 19.0.1.5.0 | PASS |
| PROD | base 19.0.1.4.0, ncf 19.0.1.5.0 | PASS |

**Backup PROD:** `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-02_220052`

## Qué se implementó

- Campo **Tipo de comprobante fiscal predeterminado** en `res.partner` (junto a RNC)
- Campo **Tipo de comprobante fiscal** en `sale.order`
- Herencia automática: contacto → cotización → factura
- Display en selector: `B01 - Factura de Crédito Fiscal`, etc.

## Prioridad de resolución

1. Valor manual en factura
2. Valor heredado de cotización
3. Valor configurado en contacto
4. Heurística RNC (B01/B02)

## Escenarios validados

- Cliente B01, B02, sin configuración
- Cotización nueva hereda tipo
- Factura desde cotización conserva tipo
- Factura directa hereda contacto
- Override manual en factura
- NCF generado correctamente
- Sin modificar lógica DGII

## Verificación visual manual

1. **Contactos** → abrir cliente → campo junto a RNC
2. **Ventas** → Cotización → seleccionar cliente → ver tipo heredado
3. **Facturar** → confirmar mismo tipo en factura borrador

## Rollback

```bash
# 1. Restaurar backup
BACKUP=/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-02_220052
# postgres + filestore + custom desde backup

# 2. O revertir módulos
# justech_l10n_do_base → 19.0.1.3.0
# justech_l10n_do_ncf → 19.0.1.4.0
docker compose run --rm odoo odoo -d hellenia_prod -u justech_l10n_do_base,justech_l10n_do_ncf --stop-after-init
docker compose restart odoo
```

## Archivos de evidencia

- `validation.json` — checks automáticos
- `audit.json` — auditoría de cambios (sin tocar DGII/NCF)
- `form_ui_snippet.txt` — extracto XML vistas con campos
