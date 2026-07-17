# 03 — Mapa funcional fiscal (comportamiento real DEV)

## Leyenda

- **Esperado:** diseño Justech / DGII.
- **Real DEV:** observado en datos + código (solo lectura).

## 1–2. Clientes / Proveedores

| Ítem | Esperado | Real |
|---|---|---|
| Entrada | `res.partner` + campos Justech RNC | Activo; padrón DGII disponible |
| Validación RNC | formato + padrón | Constraints + servicios padrón |
| Riesgo | RNC inválido en factura | Contactos con fiscal contradictorio posibles (ver datos) |

## 3–4. Facturas venta / compra

| Ítem | Esperado | Real |
|---|---|---|
| Tipo comprobante | `justech_do_document_type_id` | **1539/1540** posted usan solo LATAM type; Justech type casi vacío |
| NCF | `justech_do_ncf` o FDP unificado | **1540** en `l10n_latam_document_number`; **1** en `justech_do_ncf` |
| Secuencia | rango Justech por compañía | Rangos existen; consumo histórico vía Adel/LATAM |
| Efecto contable | asiento balanceado | GL diff 0 |
| Efecto fiscal | 606/607 | Reportes existen; dependencia de campos DGII en move |

## 5–7. NC / ND / reembolsos

Cubiertos por motor NCF + `account_debit_note`; volumen DEV bajo (out_refund 5–7). Requiere UAT dedicado en remediación.

## 8. Retenciones

Módulo `justech_l10n_do_payments_withholding` instalado; tablas `justech_do_withholding_catalog`, líneas de pago. Alimenta 623.

## 9–10. NCF emitidos / recibidos

- Emitidos: ventas/out + compras emitidos (B11/B13/B14/B15/B17) vía rangos.
- Recibidos: LATAM `l10n_latam_document_number` (proveedor).
- Modo: `justech_do_purchase_registration_mode`.

## 11–13. Rangos / secuencias / tipos

14 rangos activos, 4 empresas, sin solapes. Tipos Justech en catálogo; uso en moves residual.

## 14–17. Ingreso / bienes / formas pago / impuestos

Campos DGII en `account.move` (`justech_do_income_type_607`, `justech_do_expense_type_*`, gov retention, foreign 609). Clasificador en reports.

## 18. Reportes DGII

Exporters 606–623 presentes. En BD: varias 606 validadas, 607 validado, 623 draft; poca evidencia 608/609 generada.

## 19. Anulación NCF

Wizard `justech.do.ncf.void.wizard` + campos void en move.

## 20. Alertas NCF

**Baseline congelada.** Una actividad/`res.company`, sin correo. Cron diario activo. DEV: 0 actividades NCF abiertas, 0 mail NCF.

## 21. Multiempresa

JUSTECH(1), PlugSafe(2), Just Office(3), Omni(4) — todas `justech_do_fiscal_enabled=true`, RNC propios, umbrales idénticos.

## 22. Roles

Grupos definidos; población insuficiente (ver seguridad).

## 23. e-CF

Stack `justech_ecf_*` instalado; cron cola cada 1 min activo.
