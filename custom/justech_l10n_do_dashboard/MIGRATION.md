# Migración — justech_l10n_do_dashboard

## Instalación inicial 19.0.1.0.0

### Prerequisitos

- `justech_l10n_do_base` ≥ 19.0.1.6.0
- `justech_l10n_do_ncf` ≥ 19.0.1.8.0

### Instalación (lab)

```bash
odoo -i justech_l10n_do_dashboard -d justech_lab --stop-after-init
```

### Desinstalación

Seguro: solo elimina menú y registro placeholder. No afecta NCF ni contabilidad.

### Rollback

```bash
odoo --uninstall justech_l10n_do_dashboard -d justech_lab --stop-after-init
```
