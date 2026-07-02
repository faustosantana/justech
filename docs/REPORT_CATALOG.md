# Catálogo de Reportes — Hellenia

**Fase:** 8  
**Ambiente:** DEV  
**Fecha:** 2026-06-30  
**Estado bloque:** **PASS CON OBSERVACIONES**

---

## 1. Módulos de reportes instalados

| Módulo | Estado |
|--------|--------|
| `account_reports` | Instalado (EE) |
| `l10n_do_reports` | Instalado |
| `justech_l10n_do_reports` | Instalado |
| `spreadsheet_dashboard` | Instalado (EE) |

---

## 2. Clasificación de reportes

### 2.1 Operativos

| Reporte | Ruta Odoo | Módulo | Estado |
|---------|-----------|--------|--------|
| Existencias / Inventario disponible | Inventario → Informes | `stock` | ✅ Disponible |
| Movimientos de stock | Inventario → Informes | `stock` | ✅ |
| Pedidos pendientes entrega | Inventario → Operaciones | `stock` | ✅ |
| Cotizaciones abiertas | Ventas → Pedidos | `sale` | ✅ |
| PO pendientes recepción | Compras → Pedidos | `purchase` | ✅ |

### 2.2 Gerenciales

| Reporte | Ruta | Módulo | Estado |
|---------|------|--------|--------|
| Dashboards EE | Tableros | `spreadsheet_dashboard` | ✅ |
| Análisis ventas | Ventas → Informes | `sale` | ✅ |
| Análisis compras | Compras → Informes | `purchase` | ✅ |

### 2.3 Contables

| Reporte | Ruta | Estado |
|---------|------|--------|
| Balance de comprobación | Contabilidad → Informes | ✅ EE |
| Estado de resultados | Contabilidad → Informes | ✅ EE |
| Balance general | Contabilidad → Informes | ✅ EE |
| Libro mayor | Contabilidad → Informes | ✅ EE |
| Cuentas por cobrar vencidas | Contabilidad → Informes | ✅ EE |
| Cuentas por pagar vencidas | Contabilidad → Informes | ✅ EE |
| Flujo de caja | Contabilidad → Informes | ✅ EE |
| Ganancia por producto | Contabilidad → Informes | ✅ EE |

### 2.4 Fiscales (RD)

| Reporte | Formato | Módulo | Estado |
|---------|---------|--------|--------|
| Compras DGII | 606 | `justech_l10n_do_reports` | ✅ MVP |
| Ventas DGII | 607 | `justech_l10n_do_reports` | ✅ MVP |
| NCF anulados | 608 | `justech_l10n_do_reports` | ✅ MVP |
| Reportes `l10n_do_reports` | Varios | Estándar | ✅ Instalado |

### 2.5 Inventario (analíticos)

| Reporte | Estado |
|---------|--------|
| Valoración inventario | ✅ `stock_account` |
| Rotación (stock) | ✅ EE |
| Reglas reorden | N/A — sin configurar |

### 2.6 Ventas / Rentabilidad

| Reporte | Estado |
|---------|--------|
| Margen por producto | ✅ `account_reports` |
| Ventas por cliente | ✅ |
| Ventas por vendedor | ✅ (requiere vendedores UAT) |

### 2.7 Compras

| Reporte | Estado |
|---------|--------|
| Análisis compras por proveedor | ✅ |
| Precio histórico compra | ✅ |

---

## 3. Reportes prioritarios Hellenia

Ver `config/company/reports_priority.yaml`:

| ID | Reporte | Estado Fase 8 |
|----|---------|---------------|
| R-01 | Inventario disponible | ✅ Disponible |
| R-02 | Ventas | ✅ Disponible |
| R-03 | Compras | ✅ Disponible |
| R-04 | Ganancia por producto | ✅ EE |
| R-05 | Cuentas por cobrar | ✅ EE |
| R-06 | Flujo de caja | ✅ EE |

---

## 4. Faltantes identificados

| Reporte | Categoría | Prioridad | Notas |
|---------|-----------|-----------|-------|
| Formato DGII oficial exacto (TXT/XML) | Fiscal | P1 | MVP genera datos; formato oficial puede diferir |
| Reporte showroom / piezas en exposición | Operativo | P3 | No estándar — evaluar custom futuro |
| Margen por categoría decoración | Gerencial | P2 | Pivot estándar posible |
| Antigüedad inventario por categoría | Inventario | P2 | EE stock reports |
| POS / cierre caja | Operativo | N/A | POS no instalado |
| CRM pipeline | Ventas | N/A | CRM prohibido |

---

## 5. Validación

| Check | Resultado |
|-------|-----------|
| `account_reports` | ✅ |
| `justech_l10n_do_reports` | ✅ |
| `l10n_do_reports` | ✅ |

```
Estado: PASS CON OBSERVACIONES
Causa: formato DGII oficial y reportes custom showroom pendientes
Impacto: UAT reportes estándar ejecutable
Prioridad: P1 validación formato 606/607/608 con contador
Propuesta: incluir export reportes en escenarios UAT fiscal
```

---

## 6. Referencias

- `config/company/reports_priority.yaml`
- [DOMINICAN_LOCALIZATION_CONFIGURATION.md](DOMINICAN_LOCALIZATION_CONFIGURATION.md)
