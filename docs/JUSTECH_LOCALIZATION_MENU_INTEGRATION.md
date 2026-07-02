# Fase 15 — Integración nativa Localización Justech

**Objetivo:** Que la localización dominicana se perciba como parte nativa de Odoo, no como módulo técnico aislado.

---

## 1. Estructura integrada

### Contabilidad → Configuración → Localización Dominicana

| Menú | Acción | Descripción |
|------|--------|-------------|
| Tipos de NCF | `justech.do.fiscal.document.type` | B01, B02, B03, B04, B11, B13, etc. |
| Rangos NCF | `justech.do.ncf.range` | Autorizaciones DGII |
| Consumo NCF | `justech.do.ncf.consumption` | Secuencias consumidas |
| Configuración fiscal | `res.company` (pestaña fiscal) | Habilitación fiscal, alertas NCF |

### Contabilidad → Reportes → Reportes DGII

| Menú | Acción |
|------|--------|
| 606 — Compras | Wizard con `default_report_type=606` |
| 607 — Ventas | Wizard con `default_report_type=607` |
| 608 — Anulados | Wizard con `default_report_type=608` |
| Historial fiscal | `justech.do.fiscal.report` |

### Contabilidad → Auditoría

| Menú | Acción |
|------|--------|
| Consumo NCF | Consumos activos (`state=consumed`) |
| NCF anulados | Consumos anulados (`state=voided`) |
| Historial fiscal | Reportes generados |

## 2. Permisos

- `group_justech_do_fiscal_user` — ver menús fiscales y reportes
- `group_justech_do_fiscal_manager` — gestión completa
- **Nuevo:** `account.group_account_manager` y `account.group_account_user` heredan `group_justech_do_fiscal_user`

## 3. Etiquetas en español

Todas las acciones y menús Justech renombrados en XML y reforzados por `hellenia_ui.apply_menu_labels()`.

## 4. Facturas, clientes, productos

| Área | Integración existente |
|------|----------------------|
| Facturas | NCF, tipo comprobante, estado fiscal en `account_move_views.xml` |
| Clientes/Proveedores | RNC, tipo identificación en `res_partner_views.xml` |
| Productos | Impuestos ITBIS 18% vía localización RD |

## 5. Visibilidad validada

Usuario `it@justech.do` ve: **Localización Dominicana**, **Reportes DGII**, **Auditoría**.

Usuario contabilidad (`usuario.contabilidad.demo15`) ve los mismos menús fiscales.

Usuario ventas/compras/inventario/normal: **no** ven menús fiscales ni Contabilidad.
