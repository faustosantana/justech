# Configuración Comercial — Hellenia

**Fase:** 8 — Parametrización funcional  
**Ambiente:** DEV  
**Fecha:** 2026-06-30  
**Estado bloque:** **PASS CON OBSERVACIONES**

---

## 1. Módulos

| Módulo | Estado |
|--------|--------|
| `sale` | Instalado |
| `sale_stock` | Instalado (bridge) |
| `sale_enterprise` | Instalado |
| `contacts` | Instalado |

---

## 2. Parametrización aplicada

### 2.1 Equipos comerciales

| Equipo | Uso |
|--------|-----|
| Sales | Equipo estándar Odoo (heredado) |
| Ventas Hellenia | Equipo oficial creado Fase 8 |

### 2.2 Condiciones de pago

| Nombre | Días | Origen |
|--------|------|--------|
| Pago inmediato | 0 | Fase 8 |
| 15 días | 15 | Fase 8 |
| 30 días | 30 | Fase 8 |
| 45 días | 45 | Fase 8 |
| 60 días | 60 | Fase 8 |
| Immediate Payment, 15/21/30/45 Days, etc. | Varios | Estándar Odoo |

**Decisión pendiente Hellenia:** plazos comerciales oficiales por tipo de cliente.

### 2.3 Listas de precios

| Lista | Moneda | Estado |
|-------|--------|--------|
| Default | DOP | Estándar |
| Lista pública DOP | DOP | Creada Fase 8 |

**Pendiente:** reglas de precio por categoría, descuentos por volumen, listas USD.

### 2.4 Monedas

| Moneda | Uso |
|--------|-----|
| DOP | Principal |
| USD | Cuenta bancaria ahorro — tipo cambio manual |

---

## 3. Flujos configurados (estándar Odoo)

| Flujo | Estado |
|-------|--------|
| Cotización → Pedido | ✅ Estándar |
| Pedido → Entrega | ✅ `sale_stock` |
| Pedido → Factura | ✅ Estándar |
| Factura con ITBIS 18% | ✅ Validado Fase 4/6 |

---

## 4. Pendiente decisión Hellenia

| Item | Impacto | Prioridad |
|------|---------|-----------|
| Política de descuentos máximos | Ventas | P1 |
| Política de devoluciones | Ventas + Inventario | P1 |
| Política de garantías | Post-venta | P2 |
| Canales de venta (tienda, online, showroom) | Equipos / etiquetas | P2 |
| Vendedores asignados | Usuarios UAT | P0 |
| Tipos de cliente (mayorista, retail, interiorismo) | Categorías partner | P2 |

---

## 5. Datos existentes (no reales)

| Ref | Tipo | Notas |
|-----|------|-------|
| PHASE4-CUST | Cliente prueba | Fase 4 E2E |
| UAT-PILOT-CUST-001 | Cliente piloto | Fase 8 — para UAT |
| Registros adicionales | Clientes | Residuales DEV (5 total) |

**No cargar clientes reales hasta UAT aprobado.**

---

## 6. Validación

| Check | Resultado |
|-------|-----------|
| Módulo ventas | ✅ |
| Equipos comerciales | ✅ |
| Plazos de pago | ✅ |
| Listas de precios | ✅ |

```
Estado: PASS CON OBSERVACIONES
Causa observaciones: políticas comerciales pendientes decisión negocio
Impacto: UAT puede ejecutarse con políticas provisionales documentadas
Prioridad pendientes: P1 descuentos/devoluciones
Propuesta: workshop 1h Hellenia + Justech antes de UAT ventas
```

---

## 7. Referencias

- [PHASE4_COMMERCIAL_CORE.md](PHASE4_COMMERCIAL_CORE.md)
- [ROLE_MATRIX.md](ROLE_MATRIX.md) — rol Ventas, Caja, Atención cliente
