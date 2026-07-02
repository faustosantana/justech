# Matriz oficial de roles — Hellenia

**Versión:** 1.0 (Fase 7.5)  
**Fecha:** 2026-06-30  
**Estado:** **DISEÑO APROBADO PARA IMPLEMENTACIÓN** — usuarios funcionales **no creados aún**

---

## 1. Principios

1. **Mínimo privilegio** — cada rol recibe solo lo necesario para su función.
2. **Separación fiscal** — operaciones NCF sensibles requieren Fiscal Manager para void y rangos.
3. **TI separado** — `it@justech.do` es el único administrador técnico; `admin` solo emergencia.
4. **Sin POS** — roles POS omitidos hasta fase POS explícita.

---

## 2. Resumen de roles

| # | Rol Hellenia | Grupo Odoo base | Usuarios previstos |
|---|--------------|-----------------|-------------------|
| 1 | Gerencia General | Manager multi-módulo | 1–2 |
| 2 | Contabilidad | Accounting + Fiscal | 2–4 |
| 3 | Caja | Accounting Invoicing + Payments | 1–3 |
| 4 | Compras | Purchase User/Manager | 1–3 |
| 5 | Ventas | Sales User/Manager | 2–5 |
| 6 | Inventario | Inventory User/Manager | 1–3 |
| 7 | Atención al cliente | Sales User (limitado) | 1–3 |
| 8 | Administrador TI | Ya implementado (`it@justech.do`) | 1 |

---

## 3. Matriz detallada de permisos

Leyenda: **✓** permitido | **R** solo lectura | **—** sin acceso | **M** requiere manager

### 3.1 Gerencia General

| Área | Permiso | Grupos Odoo 19 |
|------|---------|----------------|
| Dashboards / reportes ejecutivos | ✓ | `spreadsheet_dashboard` (lectura), Accounting reports |
| Ventas — totales y margen | R | `sales_team.group_sale_manager` |
| Compras — totales | R | `purchase.group_purchase_manager` |
| Inventario — valorización | R | `stock.group_stock_manager` |
| Contabilidad — EEFF | R | `account.group_account_readonly` o `account.group_account_manager` (solo lectura vía reglas) |
| Configuración sistema | — | Sin `base.group_system` |
| Fiscal NCF — void | — | Sin Fiscal Manager |
| Usuarios / ACL | — | |

**Grupos a asignar:**
- `sales_team.group_sale_manager` (o readonly custom)
- `purchase.group_purchase_manager` (readonly)
- `stock.group_stock_manager` (readonly)
- `account.group_account_readonly`

---

### 3.2 Contabilidad

| Área | Permiso | Grupos Odoo 19 |
|------|---------|----------------|
| Plan contable / asientos | ✓ | `account.group_account_user` |
| Facturas cliente/proveedor | ✓ | `account.group_account_invoice` |
| Conciliación bancaria | ✓ | `account.group_account_user` + EE accountant |
| Reportes DGII 606/607/608 | ✓ generar/exportar | `justech_l10n_do_base.group_justech_do_fiscal_user` |
| Rangos NCF — crear/editar | M | `justech_l10n_do_base.group_justech_do_fiscal_manager` |
| Void NCF | M | Fiscal Manager |
| Cierre período | M | `account.group_account_manager` |
| Configuración impuestos | ✓ | `account.group_account_manager` |
| Usuarios | — | |

**Grupos a asignar:**
- `account.group_account_manager`
- `justech_l10n_do_base.group_justech_do_fiscal_manager`

---

### 3.3 Caja

| Área | Permiso | Grupos Odoo 19 |
|------|---------|----------------|
| Facturas de venta — crear/publicar | ✓ | `account.group_account_invoice` |
| Registro de pagos clientes | ✓ | `account.group_account_invoice` |
| NCF — asignación automática al publicar | ✓ (sin void) | `justech_l10n_do_base.group_justech_do_fiscal_user` |
| Notas de crédito | ✓ con aprobación | `account.group_account_invoice` |
| Reportes DGII | R | Fiscal User |
| Rangos NCF | — | |
| Void NCF | — | |
| Compras / inventario | — | |

**Grupos a asignar:**
- `account.group_account_invoice`
- `justech_l10n_do_base.group_justech_do_fiscal_user`
- `sales_team.group_sale_salesman` (opcional, si crean cotizaciones)

---

### 3.4 Compras

| Área | Permiso | Grupos Odoo 19 |
|------|---------|----------------|
| Órdenes de compra | ✓ | `purchase.group_purchase_user` |
| Facturas proveedor | ✓ | `account.group_account_invoice` |
| NCF compras B11/B13 | ✓ | Fiscal User |
| Aprobar OC > umbral | M | `purchase.group_purchase_manager` |
| Contabilidad avanzada | — | |
| Void NCF | — | |

**Grupos a asignar:**
- `purchase.group_purchase_user`
- `account.group_account_invoice`
- `justech_l10n_do_base.group_justech_do_fiscal_user`

---

### 3.5 Ventas

| Área | Permiso | Grupos Odoo 19 |
|------|---------|----------------|
| Cotizaciones / pedidos | ✓ | `sales_team.group_sale_salesman` |
| Facturación desde pedido | ✓ | `sales_team.group_sale_salesman` + `account.group_account_invoice` |
| Descuentos / precios | M según política | `product.group_product_manager` (solo si aplica) |
| NCF ventas B01/B02/B04 | ✓ al publicar | Fiscal User |
| Reporte 607 | R | Fiscal User |
| Void NCF | — | |

**Grupos a asignar:**
- `sales_team.group_sale_salesman`
- `account.group_account_invoice`
- `justech_l10n_do_base.group_justech_do_fiscal_user`

**Jefe ventas adicional:** `sales_team.group_sale_manager`

---

### 3.6 Inventario

| Área | Permiso | Grupos Odoo 19 |
|------|---------|----------------|
| Recepciones / entregas | ✓ | `stock.group_stock_user` |
| Ajustes de inventario | M | `stock.group_stock_manager` |
| Ubicaciones / almacenes | R | `stock.group_stock_user` |
| Valorización | R | `stock.group_stock_manager` |
| Contabilidad | — | |
| Fiscal | — | |

**Grupos a asignar:**
- `stock.group_stock_user`
- Opcional supervisor: `stock.group_stock_manager`

---

### 3.7 Atención al cliente

| Área | Permiso | Grupos Odoo 19 |
|------|---------|----------------|
| Consulta pedidos / facturas | R | `sales_team.group_sale_salesman` (reglas restringidas) |
| Crear cotizaciones | ✓ | `sales_team.group_sale_salesman` |
| Publicar facturas | — | |
| Contactos | ✓ editar | `base.group_user` |
| Precios costo | — | |
| NCF / fiscal | — | |

**Grupos a asignar:**
- `sales_team.group_sale_salesman`
- Sin `account.group_account_invoice` (no publica facturas)

**Nota:** Considerar record rules adicionales por equipo de ventas en fase UAT si se requiere aislamiento.

---

### 3.8 Administrador TI (implementado)

| Área | Permiso | Estado |
|------|---------|--------|
| Settings / Technical | ✓ | `it@justech.do` activo |
| Todos los módulos admin | ✓ | 8 grupos asignados |
| Fiscal Manager | ✓ | Para soporte NCF |
| POS | — | No instalado |

**Usuario:** `it@justech.do` — DEV y TEST

---

## 4. Matriz resumida (vista rápida)

| Permiso | Gerencia | Contab. | Caja | Compras | Ventas | Invent. | At. cliente | TI |
|---------|:--------:|:-------:|:----:|:-------:|:------:|:-------:|:-----------:|:--:|
| Settings | — | — | — | — | — | — | — | ✓ |
| Contabilidad completa | R | ✓ | parcial | parcial | parcial | — | — | ✓ |
| Publicar facturas venta | — | ✓ | ✓ | — | ✓ | — | — | ✓ |
| Publicar facturas compra | — | ✓ | — | ✓ | — | — | — | ✓ |
| NCF auto | — | ✓ | ✓ | ✓ | ✓ | — | — | ✓ |
| Void NCF | — | ✓ | — | — | — | — | — | ✓ |
| Rangos NCF | — | ✓ | — | — | — | — | — | ✓ |
| Reportes DGII | R | ✓ | R | R | R | — | — | ✓ |
| Inventario operativo | R | — | — | — | — | ✓ | — | ✓ |
| Usuarios / ACL | — | — | — | — | — | — | — | ✓ |

---

## 5. Implementación (post-aprobación UAT)

1. Crear usuarios en **TEST** primero con login corporativo `@helleniadr.com`.
2. Asignar grupos según esta matriz.
3. Validar con checklist por rol (1 día por área).
4. Replicar a DEV solo si se requiere capacitación.
5. **Producción:** solo tras Go-Live aprobado.

**No ejecutado en Fase 7.5** — diseño únicamente.

---

## 6. Referencias

- [SECURITY_AUDIT.md](SECURITY_AUDIT.md)
- [USER_ACCESS_MATRIX.md](USER_ACCESS_MATRIX.md)
- [ADMINISTRATOR_GUIDE.md](ADMINISTRATOR_GUIDE.md)
