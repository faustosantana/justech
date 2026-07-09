# DUPLICATES_REPORT — HELLENIA-MENU-UAT-2

## Ocultados (active=False)

| XML ID | Motivo |
|---|---|
| `account.account_closing_menu` | Contenedor vacío; hijos movidos a Contabilidad |
| `account.account_transactions_menu` | Contenedor redundante |
| `accountant.account_assets_liabilities_menu` | Contenedor redundante; Activos/Préstamos directos |
| `justech_l10n_do_reports.menu_justech_do_reports_root` | Contenedor DGII; hijos bajo Auditoría Fiscal |

## Eliminados de raíz Contabilidad (reparentados)

| XML ID | Destino |
|---|---|
| `account.menu_action_move_journal_line_form` | Contabilidad |
| `account.menu_action_account_moves_all` | Contabilidad |

## Accesos duplicados intencionales (documentados)

| Acceso | Ubicación A | Ubicación B | Decisión |
|---|---|---|---|
| Pagos clientes/proveedores | Clientes / Proveedores | Pagos (hub) | Mantener ambos: contextual + central |
| Pagos abiertos | Clientes / Proveedores | Pagos (hub) | Mantener ambos: filtros distintos |
| Conciliar vs Conciliación bancaria | Contabilidad > Conciliar | Pagos > Conciliación bancaria | Distintos flujos Odoo; nombres estándar |

## Renombres revertidos / corregidos

| Antes | Después | Motivo |
|---|---|---|
| Conciliar apuntes | **Conciliar** | Nombre estándar Odoo es_419 |
| Operaciones contables | **Contabilidad** | Alineado a propuesta UAT-2 |
