# Hellenia UI (`hellenia_ui`)

**Versión Odoo:** 19.0  
**Licencia:** LGPL-3  
**Alcance:** Solo personalización de menús (sin modificar core).

## Propósito

Ajustes upgrade-safe del menú principal para Hellenia:

| Cambio | Mecanismo |
|--------|-----------|
| Ventas visible | Depende de `sale_management` + activa `sale.sale_menu_root` |
| Facturación → Contabilidad | `account.menu_finance` |
| Settings → Configuración | `base.menu_administration` |
| Ocultar Apps | `base.menu_management` → `base.group_system` |
| Ocultar Código de barras | `stock_barcode.stock_barcode_menu` → `active=False` |

## Instalación (solo PROD hasta aprobación cliente)

```bash
./scripts/apply-hellenia-ui-prod.sh
```

## Autor

Justech — https://hellenia.cloud
