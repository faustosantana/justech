# UX del selector de retenciones — Fase 18.2

## Principios de diseño

1. **Español en toda la interfaz** — nombres comprensibles para contadores dominicanos.
2. **Sin códigos técnicos visibles** — `wh_isr_gov`, `Tax Withholding`, etc. no se muestran al usuario final.
3. **Ninguna por defecto** — cada factura inicia sin retenciones seleccionadas.
4. **Filtrado inteligente** — solo retenciones aplicables al contexto actual.

---

## Ubicación en wizard

**Contabilidad → Clientes/Proveedores → Pagos → Nuevo**

En la tabla de facturas pendientes, columna **Retenciones**:

| Columna | Comportamiento |
|---------|----------------|
| Retenciones | Tags seleccionables (many2many) |
| Resumen | «Ninguna» o nombres separados por coma |
| Monto retenido | Calculado automáticamente |

Debajo, sección **Detalle retenciones por factura** (solo si hay retenciones).

---

## Comportamiento del selector

### Estado inicial

```text
Retenciones: (vacío)
Resumen: Ninguna
Monto retenido: 0.00
```

### Al hacer clic en Retenciones

Se abre el diálogo de selección con retenciones filtradas por:

```python
[
    ('active', '=', True),
    ('code', 'not in', ['RET-NONE', 'wh_none']),
    ('partner_scope', 'in', [partner_type, 'both']),
    ('move_scope', 'in', [move_scope_factura, 'both']),
    ('company_id', '=', company_id),
    ('account_id', '!=', False),
]
```

### Cobro a cliente (venta)

Opciones típicas:

- Retención 5% Gobierno
- Retención ITBIS 30%
- Retención ITBIS 100%
- Retención ISR 2%
- Retención ISR 10% Honorarios

### Pago a proveedor (compra)

Opciones típicas:

- Retención ISR 10% Proveedor Informal
- Retención ITBIS 75% Proveedor Informal
- Retención ISR 2%
- Retención ITBIS 30%
- Retención ITBIS 100%

---

## Nombres mostrados al usuario

| Antes (técnico) | Ahora (español) |
|-----------------|-----------------|
| wh_isr_gov | Retención 5% Gobierno |
| wh_itbis_30 | Retención ITBIS 30% |
| wh_isr_10 | Retención ISR 10% Proveedor Informal |
| wh_itbis_75 | Retención ITBIS 75% Proveedor Informal |
| wh_isr_fees_10 | Retención ISR 10% Honorarios |

Códigos `RET-*` solo visibles en **Administrar retenciones** (grupo contable).

---

## Totales del wizard

| Campo | Descripción |
|-------|-------------|
| Total a pagar/cobrar | Suma de montos a aplicar |
| Total retenido | Suma de retenciones de facturas seleccionadas |
| Neto a transferir | Total − Retenido |

---

## Errores evitados

- Retención de proveedor no aparece en cobro cliente (salvo alcance `both`).
- Retención inactiva no aparece tras desactivar en administración.
- Retención sin cuenta no aparece (no se puede contabilizar).
- Total retenido > monto a aplicar → mensaje de error claro en español.
