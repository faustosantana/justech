# Configuración Localización Dominicana — Hellenia

**Fase:** 8  
**Ambiente:** DEV  
**Fecha:** 2026-06-30  
**Estado bloque:** **PASS**

---

## 1. Módulos

| Módulo | Versión | Estado |
|--------|---------|--------|
| `l10n_do` | Estándar Odoo | Instalado |
| `l10n_do_reports` | Estándar | Instalado |
| `justech_l10n_do_base` | 19.0.1.1.0 | Instalado |
| `justech_l10n_do_ncf` | 19.0.1.1.0 | Instalado |
| `justech_l10n_do_reports` | 19.0.1.1.0 | Instalado |

---

## 2. Configuración empresa

| Parámetro | Valor |
|-----------|-------|
| `justech_do_fiscal_enabled` | ✅ True (Fase 8) |
| RNC | 133621282 |
| País | DO |

---

## 3. Tipos de documento NCF

| Código | Nombre | Serie | Tipo movimiento |
|--------|--------|-------|-----------------|
| 01 | Factura de Crédito Fiscal | B | out_invoice |
| 02 | Factura de Consumo | B | out_invoice |
| 03 | Nota de Débito | B | out_invoice |
| 04 | Nota de Crédito | B | out_refund |
| 11 | Comprobante de Compras | B | in_invoice |
| 13 | Gastos Menores | B | in_invoice |

**Total:** 6 tipos — datos XML módulo `justech_l10n_do_base`.

---

## 4. Diarios fiscales

| Diario | `justech_do_use_ncf` | Fase 8 |
|--------|---------------------|--------|
| INV (ventas) | ✅ True | Habilitado |
| FACTU (compras) | ✅ True | Habilitado |

---

## 5. Rangos NCF

| Estado DEV | Detalle |
|------------|---------|
| Rangos configurados | 1 (prueba MVP) |
| Rangos DGII reales | **Pendiente** — requiere autorización Hellenia |

**No usar rangos DEV para documentos fiscales reales.**

Parámetros rango estándar:
- Serie B, prefijo según tipo
- Secuencia numérica
- Fecha vigencia
- Alerta días (`justech_do_ncf_alert_days` en empresa)

---

## 6. Permisos fiscales

| Grupo | XML ID | Usuarios DEV |
|-------|--------|--------------|
| Fiscal User | `group_justech_do_fiscal_user` | 0 |
| Fiscal Manager | `group_justech_do_fiscal_manager` | `it@justech.do` |

**UAT:** asignar Fiscal Manager a rol Contabilidad según [ROLE_MATRIX.md](ROLE_MATRIX.md).

---

## 7. Operaciones fiscales

| Operación | Estado | Control |
|-----------|--------|---------|
| Asignación automática NCF | ✅ | Al publicar factura |
| Nota de crédito B04 | ✅ | Validado Fase 6 |
| Nota de débito B03 | ✅ | Tipo documento disponible |
| Compras B11/B13 | ✅ | Validado Fase 6 |
| Anulación (void) | ✅ | Solo Fiscal Manager — Sprint 0 |
| Impresión PDF NCF | ✅ | 31 KB+ validado |
| Reporte 606 compras | ✅ | MVP |
| Reporte 607 ventas | ✅ | MVP |
| Reporte 608 anulados | ✅ | MVP |

---

## 8. Responsables (documentados)

| Nombre | Rol | Usuario Odoo |
|--------|-----|--------------|
| Glys Nuñez | Contadora oficial | Pendiente UAT |
| Milagros Martínez | Supervisora | Pendiente UAT |

Ver `config/company/responsibles.yaml`.

---

## 9. Pendientes

| Item | Prioridad |
|------|-----------|
| Rangos NCF autorizados DGII | P0 |
| Validación formatos DGII oficiales vs MVP | P1 |
| e-CF / facturación electrónica | Futuro (fuera MVP) |
| Usuario Fiscal Manager funcional | P0 (UAT) |

---

## 10. Validación

| Check | Resultado |
|-------|-----------|
| Fiscal habilitado | ✅ |
| 6 tipos documento | ✅ |
| Diarios NCF | ✅ |
| PHASE6_MVP | ✅ 19/19 checks |

```
Estado: PASS
Observaciones: rangos DGII reales pendientes (esperado en DEV)
```

---

## 11. Referencias

- [NCF_IMPLEMENTATION.md](NCF_IMPLEMENTATION.md)
- [DOMINICAN_FISCAL_CERTIFICATION.md](DOMINICAN_FISCAL_CERTIFICATION.md)
- [PHASE6_TEST_RESULTS.md](PHASE6_TEST_RESULTS.md)
