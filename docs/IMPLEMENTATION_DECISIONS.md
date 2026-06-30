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

**Mantenido por:** Justech — Consultoría Odoo Enterprise
