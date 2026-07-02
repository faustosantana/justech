# Hellenia Account (`hellenia_account`)

**Estado:** Funcional — Fase 16 pagos/bancos  
**Versión Odoo:** 19.0.1.0.1  
**Licencia:** LGPL-3

## Descripción

Extensiones contables upgrade-safe para Hellenia:

- Diarios bancarios DOP (`BNKD`) y USD (`BNKU`) vinculados a López de Haro
- Métodos de pago en español: Transferencia, Efectivo, Tarjeta, Cheque
- Wizard de pago con facturas pendientes y NCF visible
- Activación retenciones RD clave (`l10n_do`)

## Dependencias

`hellenia_base`, `account`, `justech_l10n_do_ncf`, `l10n_do_check_printing`

## Instalación TEST

```bash
bash scripts/run-phase16-payments-test.sh
```

## Autor

Justech — https://hellenia.cloud
