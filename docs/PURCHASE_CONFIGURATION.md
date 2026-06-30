# Configuración de Compras — Hellenia

**Fase:** 8  
**Ambiente:** DEV  
**Fecha:** 2026-06-30  
**Estado bloque:** **PASS CON OBSERVACIONES**

---

## 1. Módulos

| Módulo | Estado |
|--------|--------|
| `purchase` | Instalado |
| `purchase_stock` | Instalado |
| `purchase_accountant` | Instalado (EE) |

---

## 2. Parametrización actual

### 2.1 Flujo estándar

| Etapa | Estado Odoo | Configuración |
|-------|-------------|---------------|
| RFQ (solicitud cotización) | `draft` | Estándar |
| PO confirmada | `purchase` | Estándar |
| Recepción parcial/total | `purchase_stock` | Estándar |
| Factura proveedor | `account` + diario FACTU | NCF habilitado |
| Devolución | `stock` return | Estándar |

Estados PO disponibles: `draft`, `sent`, `to approve`, `purchase`, `done`, `cancel`

### 2.2 Condiciones de pago

Comparten plazos con módulo contable (ver [COMMERCIAL_CONFIGURATION.md](COMMERCIAL_CONFIGURATION.md)).

### 2.3 Diario compras

| Código | Tipo | NCF |
|--------|------|-----|
| FACTU | purchase | ✅ `justech_do_use_ncf=True` (Fase 8) |

---

## 3. Proveedores

### 3.1 Estructura documentada (sin cargar)

Ver `config/company/suppliers.yaml`:

- Raudo RD
- Pack-it Dominicana
- LM Inversiones Inmobiliarias SRL
- Glys Nuñez (validar rol proveedor vs responsable)

### 3.2 Datos piloto en DEV

| Ref | Nombre | Origen |
|-----|--------|--------|
| PHASE4-VEND | Proveedor prueba Fase 4 | E2E |
| UAT-PILOT-VEND-001 | Proveedor Piloto UAT | Fase 8 |

**Total proveedores DEV:** 3

---

## 4. Pendiente decisión Hellenia

| Item | Impacto | Prioridad | Propuesta |
|------|---------|-----------|-----------|
| Aprobaciones de compra (umbral DOP) | Control gastos | P1 | Activar reglas estándar `purchase` con umbral acordado |
| Compras internacionales | Moneda USD, aranceles | P2 | Validar si Hellenia importa; posición fiscal |
| Tipos de proveedor | Clasificación | P2 | Etiquetas partner |
| Retenciones en compras | Fiscal | P1 | Validar con contador |
| Carga proveedores reales | Operación | P0 | Post-aprobación UAT |

---

## 5. Compras internacionales

**Estado:** Pendiente validar con Hellenia.

Si aplica:
- Moneda USD en PO
- Posición fiscal correspondiente
- Documentación aduanera fuera de alcance MVP

---

## 6. Validación

| Check | Resultado |
|-------|-----------|
| Módulo compras | ✅ |
| Estados PO | ✅ |
| Proveedores piloto | ✅ |
| Diario FACTU + NCF | ✅ |

```
Estado: PASS CON OBSERVACIONES
Causa: aprobaciones y proveedores reales pendientes
Impacto: UAT compras ejecutable con proveedor piloto
Prioridad: P1 aprobaciones, P0 proveedores reales para UAT completo
Propuesta: definir umbral aprobación (ej. >50,000 DOP requiere gerencia)
```

---

## 7. Referencias

- [PHASE4_COMMERCIAL_CORE.md](PHASE4_COMMERCIAL_CORE.md)
- [DOMINICAN_LOCALIZATION_CONFIGURATION.md](DOMINICAN_LOCALIZATION_CONFIGURATION.md) — B11/B13 compras
