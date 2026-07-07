# GO-LIVE-UX — Reporte final PROD

**Fecha:** 2026-07-07  
**Base:** hellenia_prod  
**Resultado validación:** PASS  
**Healthcheck:** PASS (1 WARN Traefik logs, no bloqueante)

## 1. Problemas visuales corregidos

- Formulario de producto: eliminado título "Precios Comerciales Justech"; bloque Venta/Compra en Información general.
- Impuestos de venta dentro del grupo Venta; impuestos de compra dentro del grupo Compra (sin mezclar).
- Campos nativos duplicados (list_price, standard_price, taxes) ocultos en su ubicación original.
- Impuesto compra renombrado de "18% Cost Good" → "18% ITBIS Compras" (mismo 18%, type_tax_use=purchase).
- 11 rangos NCF renombrados (eliminados COA, SMOKE, FISCALRD, P13, etc.).

## 2. Menús restaurados

- Contabilidad → Configuración: Plan de cuentas, Impuestos, Diarios, Monedas, Tasas de cambio, Posiciones fiscales (estándar Odoo).
- Localización Dominicana separada bajo Configuración (no reemplaza menús estándar).
- Auditoría reparentada bajo Configuración → Justech (no app raíz).
- Menú plataforma Justech/Multimoneda oculto del menú principal.

## 3. Textos limpiados

| Antes | Después |
|-------|---------|
| PRECIOS COMERCIALES JUSTECH | (sin título; grupos Venta/Compra) |
| COA3 B01, SMOKE P13.4 B02, FISCALRD Bxx | Nombres DGII oficiales |
| 18% Cost Good | 18% ITBIS Compras |

## 4–7. Checklist

- Impuesto compra: **Sí** — 18% ITBIS Compras
- Auditoría fuera de apps principales: **Sí** (admin y usuario normal)
- Navegación alineada Odoo Enterprise: **Sí**
- Healthcheck: **PASS**

## 8. Blocker pendiente — NCF nomenclatura

Se aplicaron nombres oficiales DGII del módulo `justech_l10n_do_base`, no la lista abreviada del brief:

| Prefijo | Solicitado en brief | Aplicado (DGII/módulo) |
|---------|---------------------|------------------------|
| B02 | Consumo Final | Factura de Consumo |
| B11 | Compras para Gastos | Comprobante de Compras |
| B14 | Régimen Especial… | Regímenes Especiales… |
| B16 | Exportaciones | Comprobante para Exportaciones |
| B17 | Pagos al Exterior | Comprobante para Pagos al Exterior |

**Acción:** Confirmar si mantener nomenclatura DGII oficial o adoptar etiquetas abreviadas del brief.

## Evidencia

- `validation.json` — 20/20 checks PASS
- `data_cleanup.json` — 11 NCF + 1 impuesto
- `healthcheck.log` — PASS
