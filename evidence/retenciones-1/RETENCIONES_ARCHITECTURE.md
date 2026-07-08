# RETENCIONES-1 — Arquitectura del módulo Justech

**Módulo técnico:** `justech_l10n_do_payments_withholding`
**Producto comercial / código de licencia:** `payments_withholding_rd`
**Nombre visible:** Pagos y Retenciones Dominicanas

---

## Problema de partida

El motor de retenciones está **entregado y activo en `hellenia_account`**, y
`justech_l10n_do_reports` (DGII 623) **depende de él** leyendo sus campos
(`hellenia_withholding_line_ids`, `catalog_id.code`). No se puede mover la lógica de golpe
sin romper esa dependencia ni la instalación del cliente Hellenia.

## Estrategia: extracción en dos etapas

### Etapa A — Empaquetado no destructivo (implementada y validada en TEST)

Se crea `justech_l10n_do_payments_withholding` como **módulo oficial Justech** que:

1. **Registra** la personalización `payments_withholding_rd` en el catálogo comercial,
   extendiendo `justech.license.service` (`_inherit`) para **añadir** (no reemplazar) la
   entrada al whitelist `REAL_JUSTECH_CUSTOMIZATIONS` y al `LICENSE_WIZARD_CUSTOMIZATION_CODES`.
2. **Declara** un `justech.commercial.product` `payments_withholding_rd` con su línea de feature
   y mapeo de módulos técnicos (data XML, `noupdate="1"`).
3. **Publica** los interruptores ON/OFF comerciales (10) para el panel de administración.
4. **Se auto-registra** como feature vía `justech_register` + `post_init_hook`.
5. **NO mueve** ningún modelo, vista, campo ni XML ID de `hellenia_account`.

Visibilidad: `technical_modules_all = ("justech_l10n_do_payments_withholding",)` ⇒ la
personalización **solo aparece si el módulo técnico está instalado** (requisito FASE 4).

**Dependencias del módulo (Etapa A):**
```
account
justech_l10n_do_base
justech_l10n_do_ncf
justech_l10n_do_reports   (arrastra hellenia_account, donde vive el motor hoy)
justech_modules           (servicio de licencias/catálogo)
```

**Diagrama (Etapa A):**
```
account ─┐
         ├─ justech_l10n_do_base ─ justech_l10n_do_ncf ─ hellenia_account (MOTOR)
         │                                                     ▲
         │                                     justech_l10n_do_reports (623) ─┐
         │                                                                    │
justech_modules (catálogo/licencias) ◄── justech_l10n_do_payments_withholding ┘
                                          (empaquetado + switches + feature)
```

### Etapa B — Reubicación física del motor (propuesta, requiere aprobación)

Mover progresivamente a `justech_l10n_do_payments_withholding`:
- Modelos `hellenia.withholding.catalog`, `hellenia.payment.withholding.line`,
  `hellenia.payment.application.line` y las extensiones de `account.payment` / `account.move`.
- Wizards, vistas y reportes de retención.

Con **migración controlada** de XML IDs (alias / `ir.model.data` re-parenting) para no romper
referencias, y **manteniendo los nombres de modelo** (`hellenia.*`) o creando shims `_inherit`.
Tras el traslado:
- `hellenia_account` pasa a **depender** de `justech_l10n_do_payments_withholding` (o queda como
  capa de compatibilidad que solo re-exporta).
- `justech_l10n_do_reports` cambia su dependencia a `justech_l10n_do_payments_withholding`.

Objetivo final de dependencias (Etapa B):
```
account, justech_l10n_do_base, justech_l10n_do_ncf, justech_l10n_do_reports
        └── justech_l10n_do_payments_withholding (MOTOR + catálogo)
                     ▲                 ▲
             hellenia_account   justech_l10n_do_reports (623)
```

> La Etapa B se detalla en `RETENCIONES_MIGRATION_PLAN.md`.

---

## Contenido del módulo (Etapa A)

```
custom/justech_l10n_do_payments_withholding/
├── __init__.py
├── __manifest__.py                 # deps + justech_register + post_init_hook
├── hooks.py                        # registra feature en el catálogo (idempotente)
├── data/
│   └── justech_commercial_catalog.xml   # producto comercial + línea + mapeo módulos
└── models/
    ├── __init__.py
    └── justech_license_service.py  # _inherit: añade payments_withholding_rd al catálogo
```

## Interruptores comerciales (FASE 5)

Comerciales/documentales (no alteran el runtime fiscal todavía), listos para cableado futuro:

| Sección | Interruptores |
|---|---|
| PAGOS | Pagos con retención · Validaciones fiscales de pago |
| RETENCIONES | Retención ITBIS · Retención ISR · Retención a proveedores · Retención a clientes (si aplica) · Retenciones gubernamentales |
| DOCUMENTOS | Comprobantes de retención · Reporte 623 · Trazabilidad de retenciones |

Total: **10 interruptores** en 3 secciones (validado en TEST).
