# Fase 17 — Auditoría UX completa Hellenia TEST

**Fecha:** 2026-06-30  
**Ambiente:** `hellenia_test`  
**Alcance:** Módulos instalados — Ventas, Compras, Inventario, Contabilidad, Justech RD

---

## 1. Resumen ejecutivo

| Área | Hallazgos previos | Corrección Fase 17 |
|------|-------------------|-------------------|
| Formularios fiscales | Void NCF, Void Reason, Origin NCF en inglés | `hellenia_ux` + español en modelos |
| NCF visual | Abreviatura "NCF" | Bloque "Número de Comprobante Fiscal" |
| QR en PDF | Presente (no e-CF) | Eliminado |
| Pagos | Manual Payment, Checks | Fase 16 + etiquetas UX |
| Menús Justech | Parcialmente integrados | `hellenia_ui` reforzado |
| Retenciones | Solo en impuestos | Sección Retenciones en facturas |
| PDF | Algunos labels EN en core | Overrides QWeb español |

---

## 2. Módulos auditados

| Módulo | Estado UX |
|--------|-----------|
| Ventas (`sale_management`) | PASS — cotización/pedido PDF español |
| Compras (`purchase`) | PASS — PDF español |
| Inventario (`stock`) | PASS — entrega/recepción PDF español |
| Contabilidad (`account`) | PASS — etiquetas diario, fechas, pagos |
| Localización RD (`justech_l10n_do_*`) | PASS — integrada bajo Contabilidad |
| Reportes DGII | PASS — 606/607/608 español |
| Pagos (`hellenia_account`) | PASS — métodos español, wizard documentos |
| NCF (`justech_l10n_do_ncf`) | PASS — anulación wizard, banda roja |
| PDF (`hellenia_reports`) | PASS — sin QR, NCF destacado |

---

## 3. Textos inglés corregidos

| Antes | Después |
|-------|---------|
| Void NCF | Anular comprobante fiscal |
| Void Reason | Motivo de anulación |
| NCF Voided | Oculto — banda DOCUMENTO ANULADO |
| Origin NCF | NCF de origen (solo NC/ND) |
| Manual Payment / Checks | Eliminados de diarios activos |
| Dominican Fiscal | Localización Dominicana |
| Company Bank Account | Cuenta bancaria de la empresa |
| Payment Method | Método de pago |
| Journal | Diario |

---

## 4. Campos técnicos ocultos

- `justech_do_ncf_voided` — invisible en formulario
- `justech_do_origin_ncf` — solo notas crédito/débito
- `justech_do_ncf_range_id` — no expuesto en UI usuario

---

## 5. Menú esperado (nativo)

```
Contabilidad
├── Tablero
├── Clientes / Proveedores
├── Reportes → Reportes DGII (606, 607, 608, Historial)
├── Auditoría Fiscal → Consumo NCF, NCF anulados, Historial
└── Configuración → Localización Dominicana
```

---

## 6. Pendientes menores (no bloqueantes)

- Algunos mensajes de error core Odoo permanecen en inglés si idioma usuario ≠ es_DO
- Campos EE avanzados (`account_accountant`) pueden mostrar etiquetas EN sin override

---

## 7. Módulo de corrección

**`hellenia_ux` v19.0.1.0.0** — capa upgrade-safe sobre custom Justech/Hellenia.
