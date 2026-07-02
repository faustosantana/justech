# Plan de promoción PROD — Fase 17.1

## Regla obligatoria

**NO promover a PRODUCCIÓN** hasta:

1. TEST PASS 100% (Fase 17.1 + regresión 16)
2. Validación visual en UI TEST
3. **Aprobación explícita** del cliente

## Flujo

```
DEV → TEST → validación funcional → aprobación → backup PROD → promoción PROD
```

## Pre-requisitos PROD

- [ ] `evidence/phase17-1-full-validation.json` con `"ok": true`
- [ ] Regresión Fase 16 PASS
- [ ] Revisión manual PDF (B01, B02, NC, ND)
- [ ] Revisión manual wizard pagos (Clientes y Proveedores)
- [ ] Backup PROD (`scripts/backup-hellenia-prod.sh`)

## Pasos promoción (tras aprobación)

1. Merge rama `cursor/phase17-1-payments-pdf-dd85` → `main`
2. `rsync` custom a VPS PROD
3. `-u hellenia_account,hellenia_reports,hellenia_ux,hellenia_ui` en `hellenia_prod`
4. Smoke test pagos + PDF
5. Documentar en `evidence/phase17-1-prod-promotion.json`

## Rollback

- Restaurar backup PROD
- Revertir módulos a versiones anteriores (1.0.2 account, 1.0.0 ux)

## Estado actual

**PROD: NO TOCAR** — pendiente aprobación explícita post-validación TEST.
