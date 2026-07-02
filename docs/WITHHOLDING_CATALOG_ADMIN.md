# Catálogo y administración de retenciones RD — Fase 18.2

**Módulo:** `hellenia_account` v19.0.1.0.6  
**Base de datos:** solo `hellenia_test` hasta aprobación explícita  
**Menú:** Contabilidad → Configuración → Localización Dominicana → **Administrar retenciones**

---

## Por qué solo aparecía «Retención 5% Gobierno»

El catálogo tenía 7 retenciones activas, pero el selector del wizard filtraba por `partner_scope`:

| Retención | `partner_scope` anterior | Visible en cobro cliente |
|-----------|--------------------------|--------------------------|
| Retención 5% Gobierno | `customer` | Sí |
| ITBIS 30%, ITBIS 100%, ISR 2%, honorarios, informales | `supplier` | No |

En flujo **Cliente → Pagos → Nuevo**, el dominio era:

```text
partner_scope in ('customer', 'both')
```

Solo la retención gubernamental cumplía ese filtro.

### Corrección Fase 18.2

1. Ampliar alcance de retenciones aplicables en cobros: ITBIS 30/100, ISR 2% y honorarios usan `partner_scope=both` y `move_scope=both`.
2. Filtrar también por **operación** (`sale` / `purchase` / `both`) según tipo de factura.
3. Exigir **cuenta contable** en retenciones activas.
4. Renombrar códigos internos a formato claro `RET-*`.
5. Mover administración al menú de Localización Dominicana.

---

## Catálogo activo (mínimo requerido)

| Código | Nombre | Tipo | Base | Cliente | Proveedor | 606 | 607 |
|--------|--------|------|------|---------|-----------|-----|-----|
| RET-GOB-5 | Retención 5% Gobierno | ISR | Base imponible | Sí | No | No | Sí |
| RET-ITBIS-30 | Retención ITBIS 30% | ITBIS | ITBIS facturado | Sí | Sí | Sí | Sí |
| RET-ITBIS-100 | Retención ITBIS 100% | ITBIS | ITBIS facturado | Sí | Sí | Sí | Sí |
| RET-INF-ISR-10 | Retención ISR 10% Proveedor Informal | ISR | Base imponible | No | Sí | Sí | No |
| RET-INF-ITBIS-75 | Retención ITBIS 75% Proveedor Informal | ITBIS | ITBIS facturado | No | Sí | Sí | No |
| RET-ISR-2 | Retención ISR 2% | ISR | Base imponible | Sí | Sí | Sí | Sí |
| RET-HON-10 | Retención ISR 10% Honorarios | ISR | Base imponible | Sí | Sí | Sí | Sí |

### Retenciones adicionales l10n_do (inactivas por defecto)

Creadas para trazabilidad; requieren confirmación contable antes de activar:

- RET-ITBIS-30-PROF — `-30% ITBIS Prof. (N02-05)`
- RET-ITBIS-100-N01 — `-100% ITBIS (N01-11)`
- RET-ITBIS-100-R293 — `-100% ITBIS (R293-11)`
- RET-ISR-10-L253 — `-10% ISR (L253-12)`
- RET-ISR-2-MAT — `-2% ISR Mat.`

---

## Administrar retenciones

Desde la ventana nativa el usuario autorizado (`account.group_account_manager`) puede:

- Ver, crear y editar retenciones
- Activar / desactivar
- Definir porcentaje, base, tipo (ISR / ITBIS / Otro)
- Definir si aplica a cliente, proveedor o ambos
- Definir operación: venta, compra o ambas
- Asignar cuenta contable
- Marcar impacto en 606 y 607
- Agregar descripción / ayuda

El impuesto `l10n_do` vinculado solo se muestra en formulario de administración (grupo contable), no en el wizard de pagos.

---

## Sincronización automática

Al instalar/actualizar `hellenia_account`:

1. `configure_withholding_reference()` activa impuestos l10n_do clave.
2. `sync_catalog_from_taxes()` crea o actualiza el catálogo.
3. Migra registros con códigos legados `wh_*` a `RET-*`.
4. Solo activa retenciones con impuesto y cuenta contable encontrados.

---

## Bases de cálculo disponibles

| Base | Uso |
|------|-----|
| Base imponible | ISR sobre subtotal sin impuestos |
| ITBIS facturado | Retenciones ITBIS (30%, 100%, 75%) |
| Total factura | Escenarios especiales configurables |
| Monto aplicado | Retención sobre el monto a pagar/cobrar en el wizard |

---

## Selector en wizard de pagos

Cada línea de factura muestra **Retenciones: Ninguna** por defecto.

Al abrir el selector se listan todas las retenciones **activas** que cumplan:

- Compañía actual
- Cliente/proveedor según flujo
- Venta/compra según tipo de factura
- Cuenta contable definida

**Cobro cliente (ejemplo):** RET-GOB-5, RET-ITBIS-30, RET-ITBIS-100, RET-ISR-2, RET-HON-10

**Pago proveedor (ejemplo):** RET-INF-ISR-10, RET-INF-ITBIS-75, RET-ISR-2, RET-ITBIS-30, RET-ITBIS-100
