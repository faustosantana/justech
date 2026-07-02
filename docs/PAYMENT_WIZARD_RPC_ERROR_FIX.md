# Payment Wizard RPC Error Fix — Fase 17.4

## Síntoma

```
RPC_ERROR 404: Not Found
Model: hellenia.payment.partner.wizard
KeyError: 'hellenia.payment.partner.wizard'
```

Al ir a **Contabilidad → Clientes → Pagos → Nuevo**.

## Causa exacta

1. El modelo **sí existía en código** (`payment_partner_wizard.py`) y en `ir.model` (BD).
2. El upgrade `-u hellenia_account` se ejecutó en contenedor **efímero** (`docker compose run`).
3. El contenedor **odoo en ejecución** no se reinició → registry Python **sin el modelo**.
4. Logs mostraron: `Some modules have inconsistent states: ['hellenia_account', 'hellenia_ux']`.
5. Las acciones/vistas en BD ya apuntaban a `hellenia.payment.partner.wizard`, pero el worker HTTP respondía **KeyError 404**.

**No era** un nombre de modelo incorrecto ni un import faltante en código fuente (tras despliegue correcto).

## Corrección aplicada

| Cambio | Detalle |
|--------|---------|
| Paquete `wizards/` | `payment_partner_wizard.py` y `payment_register_withholding.py` movidos a `custom/hellenia_account/wizards/` |
| Imports | `hellenia_account/__init__.py` importa `wizards`; `wizards/__init__.py` importa modelos |
| Versión | `hellenia_account` **19.0.1.0.4** |
| UI | Botón **Nuevo** en listas Clientes/Proveedores → Pagos abre el wizard |
| Despliegue | `run-phase17-4-fix-payment-wizard-test.sh` hace **restart obligatorio** tras `-u` |

## Procedimiento TEST

```bash
bash scripts/run-phase17-4-fix-payment-wizard-test.sh
```

Evidencia: `evidence/phase17-4-payment-wizard-test.json`

## Regla operativa

Tras cualquier `docker compose run ... -u módulo --stop-after-init` en TEST/PROD:

```bash
docker compose restart odoo
```

`docker compose up -d odoo` **no reinicia** si el contenedor ya está corriendo.

## Producción

**NO promover** sin aprobación explícita.
