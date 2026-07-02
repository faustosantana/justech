# Fase 27 — Tipo de comprobante fiscal predeterminado en contactos

## Objetivo

Campo **Tipo de comprobante fiscal predeterminado** en `res.partner` que se hereda automáticamente a cotizaciones y facturas.

## Módulos

| Módulo | Versión | Cambios |
|--------|---------|---------|
| `justech_l10n_do_base` | 19.0.1.4.0 | Campo en contacto, display_name tipos |
| `justech_l10n_do_ncf` | 19.0.1.5.0 | Herencia SO/factura, resolución NCF |

## Prioridad de resolución

1. Valor manual en factura
2. Valor heredado de cotización
3. Valor configurado en contacto
4. Heurística RNC (B01/B02)

## Despliegue

```bash
./scripts/run-phase27-partner-default-doc-type.sh test
./scripts/run-phase27-partner-default-doc-type.sh prod
```

## Rollback

1. Restaurar backup PROD desde `backup_path.txt`
2. O revertir módulos a versiones anteriores:
   - `justech_l10n_do_base` 19.0.1.3.0
   - `justech_l10n_do_ncf` 19.0.1.4.0
3. `-u justech_l10n_do_base,justech_l10n_do_ncf --stop-after-init`

## Evidencia

- TEST: `evidence/phase27-partner-default-doc-type-test/`
- PROD: `evidence/phase27-partner-default-doc-type-prod/`
