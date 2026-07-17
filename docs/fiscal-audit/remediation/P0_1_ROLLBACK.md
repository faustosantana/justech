# P0.1 — Rollback

## Trigger

Cualquiera de: secuencia consumida inesperada, NCF duplicado, loop write, GL desbalanceado, regresión alertas, fallo multiempresa, cambio histórico.

## Pasos DEV

1. Restaurar módulos desde `/opt/odoo-dev/backups/p0_1-ncf-sot-20260717_142449/modules/*.tar.gz`
2. Restaurar dump `justech_dev.dump` si hubo corrupción de datos (no esperada)
3. `systemctl restart odoo-dev`
4. `-u` versiones previas: base 19.0.1.26.0, ncf 19.0.2.14.0, fiscal_admin 19.0.1.8.6
5. Confirmar fingerprint rangos + GL
6. Confirmar baseline alertas tag `ncf-alerts-baseline-v1`

## Git

`git revert` del commit P0.1 o checkout archivos previos.

## No improvisar

No reactivar dual_write + gate a medias en el mismo incidente.
