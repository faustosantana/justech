# Bloque 2 — Unificación pagos Justech

Fecha: 2026-07-11  
Entorno: erp.justech.do / justech_dev / feature/fiscal-standard-consolidation  
Backup: `/opt/odoo-dev/backups/fiscal-payment-unify-20260711_003036`  
Bloque 1 commit: `ba8bfbec2b4824a71ffa01588a627597ba036fd6`

## Cambios (sin commit aún)
- `justech_l10n_do_payments_withholding` 19.0.1.5.0
  - `account_move_payment.py`: factura → wizard Justech
  - prefill facturas en partner wizard
  - hooks: quitar binding UI de multi-invoice
- `justech_l10n_do_treasury` 19.0.1.4.0
  - hook reafirma legacy off; menú Pagos 6 opciones (ya existente)

## UAT
- Menú Pagos: 6 hijos activos; conciliación bancaria oculta bajo Pagos
- Legacy multi-invoice: menú inactive, binding false
- Factura `action_register_payment` → `justech.payment.partner.wizard`
- Retención 1×: residual 0, 1 pago, asiento OK, luego bank → `paid`
- Pago abierto: creado vía `treasury_operation_type=open`
- Multiempresa GL 4/4; Adel 1504

## Default fiscal partner (P2 — no corregido)
0/50 clientes con default. Factura resuelve tipo/NCF al publicar. Recomendación: inferir B01/B02 en partner como UX; obligatorio solo en factura draft.

## Riesgos
- `treasury_bank_state` puede quedar `bank_pending` con cuentas outstanding `asset_current`
- Módulo `multi_invoice_manual_payment_prod` sigue instalado (solo UI retirada)
