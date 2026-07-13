# RC6 — Contabilidad, pagos y retenciones

**Entorno:** `erp.justech.do` / DB `justech_dev` / rama `feature/fiscal-standard-consolidation`  
**Producción:** no modificada. **Commit:** pendiente de aprobación.

## Prechecks

| Check | Resultado |
|-------|-----------|
| Host | `vmi3364393` |
| Base | `justech_dev` |
| Backup | `/opt/odoo-dev/backups/auto-20260713_184356` + restore-smoke PASS |
| Login HTTP | 200 |
| GL diff | 0.00 (antes y después) |
| Snapshot | moves=2405, payments=698, reconcile=969 |

## CASO A — Catálogo de retenciones (causa raíz)

1. `company_id` era **required** con default `env.company` → forzaba copias por empresa.
2. ACL solo daba CRUD a `account.group_account_manager`. Un **Administrador Fiscal** sin ese grupo recibía **AccessError** al crear.
3. Dominios de wizard exigían `company_id = company` y `account_id != False` → ocultaban globales.
4. Constraint SQL `unique(code, company_id)` no modelaba bien globales (`NULL`).

### Arquitectura aplicada (opción B preferida)

- `company_id` **opcional**, default vacío = **global**.
- Registro con empresa = **override exclusivo**.
- Índice único `(code, COALESCE(company_id,0))`.
- Globales: `source_tax_name` / `source_tax_use`; cuenta resuelta con `get_account_for_company()`.
- Sync crea catálogo **global** (no 4 copias).

### Permisos

| Rol | Lectura | CRUD catálogo |
|-----|---------|---------------|
| Facturación / Usuario Fiscal / Responsable Fiscal | Sí | No |
| Administrador de Retenciones | Sí | Sí |
| Account Manager / Administrador Fiscal (vía imply) | Sí | Sí |

## CASO B — Menús de pagos

Contabilidad → Pagos:

1. **Pagos de clientes** → domain `[('partner_type','=','customer')]`
2. **Pagos de proveedores** → domain `[('partner_type','=','supplier')]`
3. **Todos los pagos** → domain `[]`

Conteos DEV: clientes 290 + proveedores 408 = 698 = todos.

## CASO C — Factura clickeable

- Pestaña **Facturas relacionadas** con `reconciled_invoice_ids` / `reconciled_bill_ids` (`many2many_tags`) y `move_id` en líneas de aplicación/retención.
- Smart buttons **Facturas** / **Asiento**.

## CASO D / PBNK1/2026/00210 — causa raíz

| Elemento | Valor |
|----------|-------|
| Pago | id 761, `in_process`, amount 5640.40 |
| `is_reconciled` | **True** (aplicado a factura) |
| `is_matched` / `treasury_bank_state` | False / **bank_pending** |
| Factura FC/2026/00208 | `payment_state=in_payment`, residual **0** |
| Línea CxC 11030201 | residual 0, reconciled |
| Línea outstanding 11010203 | residual **5401.40**, no reconciled |
| Retención | 239.00 |

**Causa:** la acción de “Conciliar” abría líneas de **contrapartida CxC ya conciliadas**. El usuario intentaba re-conciliar → mensaje Odoo “asientos que ya han sido conciliados”. Faltaba solo **conciliación bancaria** de la cuenta transitoria.

**Corrección:** si `is_reconciled` y `treasury_bank_state=bank_pending` → acción **Conciliar con extracto bancario** (`account.bank.statement.line` del diario). No se mutó el pago ni la factura histórica.

## Matriz de estados (sin estados inventados)

| Concepto | Campo / significado |
|----------|---------------------|
| Factura no/parcial/pagada/en proceso | `payment_state` estándar (`not_paid`/`partial`/`in_payment`/`paid`/`reversed`) |
| Pago borrador/registrado | `state` (`draft`/`in_process`/`paid`/`canceled`) |
| Aplicado a factura | `is_reconciled` |
| Pendiente banco | `treasury_bank_state=bank_pending` + outstanding abierta |
| Conciliado banco | `treasury_bank_state=bank_reconciled` / `is_matched` |

## Integridad post-cambio

| Métrica | Antes | Después |
|---------|-------|---------|
| moves | 2405 | 2405 |
| payments | 698 | 698 |
| reconcile | 969 | 969 |
| GL diff | 0.00 | 0.00 |

## Módulos tocados (DEV only)

- `justech_l10n_do_payments_withholding` → **19.0.1.6.0**
- `justech_l10n_do_treasury` → **19.0.1.6.0**
- `hellenia_ui` (menús Compras → catálogo Justech; módulo no instalado en este DEV)

## Rollback

1. Revertir código en addons a versión previa de la rama.
2. `-u justech_l10n_do_payments_withholding,justech_l10n_do_treasury`.
3. Si hace falta datos: restore `/opt/odoo-dev/backups/auto-20260713_184356`.

## Limitaciones de validación en esta corrida

- Flujos E2E de pago total/parcial/proveedor/reversión se validaron a nivel de lógica/acción y datos existentes (PBNK1); no se crearon facturas/pagos nuevos históricos.
- UX claro/oscuro/responsive: formularios usan alertas Bootstrap estándar Odoo + badges; sin CSS custom frágil.
- Reportes DGII 606/607/623: catálogo conserva flags `affects_*`; sin regeneración de reportes históricos.
