# P0.1 — Plan Producción (NO EJECUTAR aún)

1. Autorización expresa.
2. Backup Prod PG + filestore + módulos.
3. Restore test Prod.
4. Desplegar mismos commits/versiones DEV validados.
5. `-u justech_fiscal_admin,justech_l10n_do_base,justech_l10n_do_ncf` (no `-u all`).
6. Verificar flag `ncf_dual_write=false`.
7. UAT SAVEPOINT: venta B01, compra recibida, NC, 606/607 smoke.
8. Confirmar históricos 20 **no** modificados.
9. Confirmar baseline alertas.
10. GO/NO-GO documentado.

**Saneamiento de los 20 históricos:** paquete separado post-P0.1.
