# Decisiones de implementación — Hellenia Odoo Enterprise

Registro cronológico de decisiones de consultoría. Toda entrada debe ser **reproducible** y **upgrade-safe**.

---

## DEC-2026-06-30-001 — Pivot estratégico v3.0

| Campo | Valor |
|-------|-------|
| **Decisión** | Plataforma oficial = Odoo 19 EE On-Premise; no perseguir saas-19.3 |
| **Motivo** | Priorizar implementación de referencia RD sobre investigación de ramas |
| **Impacto** | GAP documentado sin bloquear proyecto |
| **Documento** | [PROJECT_STRATEGY.md](PROJECT_STRATEGY.md) |

---

## DEC-2026-06-30-002 — Infraestructura congelada post Fase 2

| Campo | Valor |
|-------|-------|
| **Decisión** | No modificar Docker, Traefik, PostgreSQL, Enterprise, imágenes |
| **Motivo** | Estabilidad; trabajo solo dentro de Odoo |
| **Impacto** | Fases 3+ vía UI / odoo shell / datos maestros |
| **Excepción** | Solo error crítico infra con aprobación explícita |

---

## DEC-2026-06-30-003 — Empresa única definitiva

| Campo | Valor |
|-------|-------|
| **Decisión** | Renombrar empresa existente (id=1) a **Hellenia, S.R.L.** — no crear segunda empresa |
| **Motivo** | Preservar plan contable `do` y localización ya cargados (TC-002) |
| **Alternativa rechazada** | Nueva empresa + recarga plan (retrabajo, riesgo datos) |
| **Evidencia** | Fase 3 apply 2026-06-30 |

---

## DEC-2026-06-30-004 — RNC oficial Hellenia

| Campo | Valor |
|-------|-------|
| **Decisión** | RNC `133621282` en `res.partner.vat` |
| **Motivo** | Documentado en INFILE-REQUIREMENTS; reemplaza ficticio TC-002 `131793916` |
| **Pendiente** | Validación escrita cliente / DGII |

---

## DEC-2026-06-30-005 — Dirección fiscal pendiente

| Campo | Valor |
|-------|-------|
| **Decisión** | No inventar dirección; limpiar datos ficticios TC-002 |
| **Motivo** | Regla proyecto: no inventar datos |
| **Impacto** | Campos street/city/zip/phone/email vacíos hasta confirmación cliente |
| **YAML** | `config/company/company.yaml` → `null` |

---

## DEC-2026-06-30-006 — Website empresa

| Campo | Valor |
|-------|-------|
| **Decisión** | `https://hellenia.cloud` en partner empresa |
| **Motivo** | Documentado en manifests custom y docs proyecto |
| **Pendiente** | Confirmar URL pública definitiva |

---

## DEC-2026-06-30-007 — Zona horaria e idioma

| Campo | Valor |
|-------|-------|
| **Decisión** | `America/Santo_Domingo` + `es_DO` en usuario `admin` |
| **Motivo** | Odoo 19 no expone `tz` en `res.company`; timezone a nivel usuario |
| **Nota** | Usuarios futuros heredarán política al crearse en fase posterior |
| **No aplicado** | Creación de usuarios operativos (fuera de alcance Fase 3) |

---

## DEC-2026-06-30-008 — Bancos estructura sin números

| Campo | Valor |
|-------|-------|
| **Decisión** | Banco López de Haro + líneas DOP corriente y USD ahorro con placeholder `PENDING-*` |
| **Motivo** | Estructura requerida; números no proporcionados |
| **Riesgo** | Placeholder debe reemplazarse antes de go-live / conciliación real |
| **YAML** | `config/company/banks.yaml` |

---

## DEC-2026-06-30-009 — Árbol categorías inventario golden

| Campo | Valor |
|-------|-------|
| **Decisión** | Crear jerarquía Inventario → Mobiliario/Decoración/… + Servicios + Consumibles |
| **Motivo** | Rubro retail mobiliario/decoración Hellenia |
| **No eliminar** | Categorías Odoo default (Goods, Expenses, Services) — upgrade-safe |
| **Inconsistencia** | CAT-01, CAT-02 documentadas en YAML |

---

## DEC-2026-06-30-010 — Proveedores solo estructura

| Campo | Valor |
|-------|-------|
| **Decisión** | No crear partners proveedor en Fase 3 |
| **Motivo** | Instrucción cliente; Fase 6 Compras |
| **Preparación** | Campos y política documentados en checklist Fase 3 |

---

## DEC-2026-06-30-011 — Sin módulos ni custom en Fase 3

| Campo | Valor |
|-------|-------|
| **Decisión** | No instalar módulos, no custom, no wizard, no permisos |
| **Motivo** | Golden config = datos maestros sobre stack TC-001/002 |
| **Contabilidad** | Validar plan/impuestos/diarios existentes — no corregir vía código |

---

## DEC-2026-06-30-012 — Logo pendiente

| Campo | Valor |
|-------|-------|
| **Decisión** | Logo, favicon y layout reportes — acción diferida hasta upload PDF/logo |
| **Prioridad formatos** | SVG > PNG transparente |
| **Proceso acordado** | Conversión automática al recibir archivo |

---

## DEC-2026-06-30-013 — Backup obligatorio pre-cambio

| Campo | Valor |
|-------|-------|
| **Decisión** | `backup-dev.sh` + `verify-backup-dev.sh` antes de apply Fase 3 |
| **Backup** | `/opt/odoo-projects/hellenia/backups/dev/2026-06-30_0440` |
| **Resultado** | Verificado OK |

---

## DEC-2026-06-30-014 — Fase 3.5 datos oficiales empresa

| Campo | Valor |
|-------|-------|
| **Decisión** | Aplicar dirección Piantini, teléfono, email oficiales desde documento empresa |
| **Fuente** | Información de la empresa para Odoo |
| **Backup** | `2026-06-30_0446` |

---

## DEC-2026-06-30-015 — Bancos definitivos

| Campo | Valor |
|-------|-------|
| **Decisión** | Banco López de Haro — DOP `4040043811`, USD `4010461048` |
| **Pendiente** | SWIFT, sucursal |

---

## DEC-2026-06-30-016 — Categorías inventario oficiales (planas)

| Campo | Valor |
|-------|-------|
| **Decisión** | 11 categorías hijas directas de Inventario (sin subárbol Mesas/Sillas Fase 3) |
| **Legacy** | Categorías Fase 3 no eliminadas — deprecated |

---

## DEC-2026-06-30-017 — Métodos de pago sin pasarelas

| Campo | Valor |
|-------|-------|
| **Decisión** | CSH1 Efectivo + líneas BNK1 Transferencia/Tarjetas/Link de pago manual |
| **Restricción** | Sin integración pasarela en esta fase |

---

## DEC-2026-06-30-018 — Sin instalar sale/stock/POS

| Campo | Valor |
|-------|-------|
| **Decisión** | Documentar requisito módulos; NO instalar en Fase 3.5 |
| **Motivo** | Restricción explícita cliente |

---

## DEC-2026-06-30-019 — Piezas únicas

| Campo | Valor |
|-------|-------|
| **Decisión** | Catálogo orientado a piezas únicas; pares como excepción documentada |
| **YAML** | `inventory_categories.yaml` → product_behavior |

---

## DEC-2026-06-30-020 — Fase 4 Commercial Core

| Campo | Valor |
|-------|-------|
| **Decisión** | Instalar solo `contacts`, `stock`, `purchase`, `sale` en DEV |
| **Excluido** | POS, Barcode, Studio, Sign, Documents, Helpdesk, CRM |
| **Motivo** | Aprobación cliente — núcleo comercial antes de POS |
| **Incidencia** | `stock_barcode` auto-instalado con `stock` → desinstalado en script |
| **Producto Odoo 19** | Stock con `type: consu` + `is_storable: True` |
| **Evidencia** | `PHASE4_VALIDATION ok: true` |
| **Backup** | `2026-06-30_0452` |
| **Supersede** | DEC-018 (ya no aplica — módulos instalados en Fase 4) |

---

## DEC-2026-06-30-021 — Fase 5 DAFC certificación

| Campo | Valor |
|-------|-------|
| **Decisión** | Certificar contabilidad/fiscal RD sin modificar config ni instalar módulos |
| **Evidencia** | `PHASE5_DAFC ok: true` — 289 cuentas, 37 impuestos, flujo con pagos |
| **P0 confirmados** | G-02 (sin l10n_latam.document.type), G-04 (sin 606/607/608) |
| **Veredicto** | CONTINUAR_CON_RESERVA_FISCAL — DEV sí; go-live fiscal DGII no |
| **Backup** | `2026-06-30_0502` |

---

**Mantenido por:** Justech — Consultoría Odoo Enterprise
