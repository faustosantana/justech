# Fase 13.2 — Validación UX en español

**Fecha:** 2026-06-30 (UTC)  
**Entornos:** TEST + PROD  
**Evidencia:** `evidence/phase13-2-validate-*.json`, script Fase 11 en PROD

---

## Resumen

| Ámbito | Estado |
|--------|--------|
| Idioma compañía `es_DO` | PASS |
| Usuarios internos `es_DO` | PASS (2/2 PROD) |
| Menús Justech fiscal | PASS — español |
| Reportes DGII | PASS — español |
| PDF factura NCF | PASS — "Tipo de documento" |
| Textos core Odoo | Parcial — ver sección 4 |

---

## 1. Menús y acciones Justech (corregidos en v1.2.0)

| Antes (inglés) | Después (español) |
|----------------|-------------------|
| Dominican Fiscal | Fiscal dominicano |
| Document Types | Tipos de documento |
| NCF Ranges | Rangos NCF |
| NCF Consumption | Consumo NCF |
| DGII Reports | Reportes DGII |
| Generate Report | Generar reporte |
| Report History | Historial de reportes |
| Regenerate | Regenerar |
| Export CSV | Exportar CSV |
| Export Excel | Exportar Excel |
| Draft / Done | Borrador / Generado |

---

## 2. Vistas y campos reportes DGII

Todos los campos visibles del modelo `justech.do.fiscal.report` usan etiquetas en español:

- Nombre, Tipo de reporte, Compañía, Desde, Hasta
- Fecha de generación, Generado por
- Subtotal gravado, Total ITBIS, Total general
- Líneas: RNC, Nombre, NCF, Tipo documento, Monto gravado, ITBIS, Total, Notas

---

## 3. PDF de factura

Plantilla `justech_l10n_do_ncf/report/report_invoice.xml`:

- **NCF** — sin cambio (término fiscal RD)
- **Tipo de documento** — corregido desde "Document Type"

---

## 4. Textos que permanecen en inglés (sin tocar core)

| Origen | Ejemplo | Motivo |
|--------|---------|--------|
| Odoo core / EE | Algunos tooltips, estados internos, nombres técnicos de impuestos en `l10n_do` | No modificable sin tocar core/Enterprise |
| Nombres impuestos `l10n_do` | "18% ITBIS", "ITBIS Exempt" | Definidos por localización oficial Odoo |
| Posiciones fiscales | "DO Domestic", "Restaurants" | Plantilla `l10n_do` |

**Mitigación aplicada:** idioma `es_DO` activo, traducciones oficiales cargadas vía `apply-phase11-spanish-and-modules.py`. Menús y flujos operativos Justech en español.

---

## 5. Validación automática

Escenario `spanish_ux_sample` en `phase13-2-validate-fiscal.py`:

- Verifica menú "Reportes DGII" presente
- **TEST:** PASS
- **PROD:** PASS

Script Fase 11 en PROD:

- `english_remainders`: 0
- `users_es_DO`: 2/2

---

## 6. Conclusión

La experiencia operativa de la localización Justech (menús, reportes, wizards, PDF NCF) está **en español**. Los residuos en inglés provienen de core/Enterprise y están documentados; no bloquean operación fiscal RD.
