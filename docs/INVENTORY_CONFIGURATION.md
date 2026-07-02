# Configuración de Inventario — Hellenia

**Fase:** 8  
**Ambiente:** DEV  
**Fecha:** 2026-06-30  
**Estado bloque:** **PASS CON OBSERVACIONES**

---

## 1. Módulos

| Módulo | Estado |
|--------|--------|
| `stock` | Instalado |
| `stock_account` | Instalado |
| `stock_enterprise` | Instalado |
| `stock_barcode` | Desinstalado (política Fase 4) |

---

## 2. Almacén

| Parámetro | Valor |
|-----------|-------|
| Nombre | Hellenia, S.R.L. |
| Código | WH |
| Ubicación stock | WH/Stock |
| Compañía | Hellenia, S.R.L. (única) |

**Sucursales adicionales:** No configuradas — pendiente validar si Hellenia opera multi-sucursal.

---

## 3. Rutas y operaciones

| Ruta / operación | Estado |
|------------------|--------|
| Rutas estándar | 3 activas |
| Recepción (incoming) | ✅ Validado Fase 4 |
| Entrega (outgoing) | ✅ Validado Fase 4 |
| Transferencias internas | ✅ Estándar |
| Devoluciones | ✅ Estándar |

---

## 4. Valoración

| Parámetro | Valor |
|-----------|-------|
| Contabilidad anglosajona | Habilitada (`anglo_saxon_accounting`) |
| Método costo | AVCO (estándar Odoo `stock_account`) |
| Cuentas valoración | Plan `do` — automáticas por categoría |

**Pendiente contador:** validar cuentas automáticas por categoría producto oficial.

### FIFO vs AVCO

| Método | Aplicabilidad Hellenia |
|--------|------------------------|
| AVCO | ✅ Actual — adecuado para mix piezas únicas + repetidas |
| FIFO | Alternativa si contador lo requiere |
| Costo específico | Para piezas únicas de alto valor — evaluar en UAT |

---

## 5. Lotes, series y trazabilidad

| Modo | Estado | Nota |
|------|--------|------|
| Sin tracking (`none`) | ✅ Default recomendado | Mayoría piezas únicas vía SKU |
| Lotes | No configurado | Pendiente política |
| Series | No configurado | Pendiente piezas de alta gama |

Ver `config/company/inventory_categories.yaml` — recomendación: `tracking: none` salvo excepción.

---

## 6. Inventario físico y ajustes

| Proceso | Estado |
|---------|--------|
| Inventario físico (cycle count) | Estándar disponible — procedimiento pendiente |
| Ajustes de inventario | Estándar — requiere permiso Inventory Manager |
| Reservas | Automáticas al confirmar SO |

---

## 7. Reabastecimiento

| Regla | Estado |
|-------|--------|
| MTO (Make to Order) | No configurado |
| MTS (Make to Stock) | Implícito estándar |
| Reglas reorden | No configuradas |

**Pendiente:** Hellenia opera principalmente con piezas únicas — reabastecimiento automático probablemente no aplica.

---

## 8. Categorías inventario

Oficiales bajo `Inventario` (11 hijas) — ver [PRODUCT_MASTER_MODEL.md](PRODUCT_MASTER_MODEL.md).

**Nota:** 3 categorías legacy Fase 3 coexisten (Decoración, etc.) — no usar para catálogo nuevo.

---

## 9. Validación

| Check | Resultado |
|-------|-----------|
| Módulo stock | ✅ |
| Almacén WH | ✅ |
| Ubicación stock | ✅ |
| Rutas | ✅ (3) |
| Valoración anglosajona | ✅ |

```
Estado: PASS CON OBSERVACIONES
Causa: lotes/series, inventario físico y reabastecimiento sin política formal
Impacto: UAT inventario ejecutable con productos piloto
Prioridad: P2 lotes/series; P1 procedimiento inventario físico
Propuesta: documentar en UAT si piezas únicas usan SKU sin serial
```

---

## 10. Referencias

- [PHASE4_COMMERCIAL_CORE.md](PHASE4_COMMERCIAL_CORE.md)
- `config/company/inventory_categories.yaml`
