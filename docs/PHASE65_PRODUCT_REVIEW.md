# Fase 6.5 — Product Review

**Pregunta:** ¿Es un producto comercial o una personalización Hellenia?  
**Fecha:** 2026-06-30

---

## 1. Veredicto

## **NO — todavía no es un producto comercial reutilizable.**

Es un **MVP técnicamente sólido** orientado a un piloto (Hellenia), con señales claras de personalización y deuda de productización.

**Calificación madurez producto:** **MVP / Pre-producto**

---

## 2. Criterios de producto comercial

| Criterio | Estado | Evidencia |
|----------|--------|-----------|
| Multi-empresa seguro | ❌ | Sin record rules |
| Multi-cliente genérico | ⚠️ | Hardcoded XML refs B01-B04 |
| i18n es_DO | ❌ | Sin `i18n/` |
| Onboarding / docs usuario | ⚠️ | README técnico mínimo |
| Cumplimiento DGII oficial | ❌ | Reportes básicos |
| Escalabilidad concurrencia | ❌ | Sin lock NCF |
| Branding neutral | ❌ | `hellenia.cloud` en manifest |
| Apps Store ready | ❌ | Sin `static/description` |
| Soporte eNCF/POS extensible | ⚠️ | Arquitectura permite, no implementado |
| Tests ≥75% cobertura | ❌ | ~48% |

**Puntuación:** 1.5 / 10 criterios plenos

---

## 3. Señales de personalización Hellenia

| Elemento | Ubicación | Debe cambiar a |
|--------|-----------|----------------|
| "Base layer for **Hellenia**" | `justech_l10n_do_base/README.md` | "Justech Dominican Localization" |
| `website: hellenia.cloud` | manifests ×3 | `https://justech.do` o neutral |
| Paths `/opt/odoo-projects/hellenia/` | docs operativos | Parametrizar en guía genérica |
| Validación ITBIS por nombre | fiscal_report.py | Tag fiscal estándar `l10n_do` |
| Tipos NCF en data global | sin company_id | Multi-company data strategy |

---

## 4. Lo que SÍ es reutilizable hoy

1. **Arquitectura 3 módulos** — vendible como suite
2. **Modelo de rangos + consumo** — patrón correcto DGII
3. **Hook pre-post sin tocar contabilidad** — portable
4. **Grupos fiscal user/manager** — base RBAC
5. **Separación reports** — extensible a DGII WS

---

## 5. Qué debe cambiarse para producto RD genérico

### Identidad producto
- [ ] Renombrar referencias Hellenia → Justech en README/manifests
- [ ] Icono, descripción Apps, screenshots
- [ ] `i18n/es_DO.po` completo

### Configurabilidad
- [ ] Matriz diario × tipo documento (eliminar hardcoded `env.ref`)
- [ ] Plantilla de rangos por defecto en post-install hook
- [ ] Wizard configuración inicial compañía RD

### Cumplimiento
- [ ] Formato TXT DGII 606/607/608
- [ ] Validación RNC con dígito verificador
- [ ] Documentación legal por tipo NCF

### Operaciones
- [ ] Record rules multi-empresa
- [ ] Lock concurrencia NCF
- [ ] Cron alertas vencimiento (`ncf_alert_days`)
- [ ] Auditoría chatter en rangos

### Calidad
- [ ] Cobertura tests ≥75%
- [ ] CI pipeline con E2E automático
- [ ] CHANGELOG semver por módulo

---

## 6. Posicionamiento recomendado

| Fase | Posicionamiento |
|------|-----------------|
| **Ahora (post Fase 6)** | "Justech l10n DO MVP — piloto Hellenia" |
| **Post hardening (Fase 6.5 fixes)** | "Justech l10n DO Core — beta privada" |
| **Post DGII TXT + eNCF** | "Justech Dominican Fiscal Suite — GA" |

---

## 7. Comparación con localizaciones Odoo maduras

| Aspecto | `l10n_do` oficial | Justech MVP |
|---------|-------------------|-------------|
| Plan contable | ✅ | Usa estándar |
| NCF operativo | ❌ | ✅ |
| Reportes DGII | Parcial EE | Básico custom |
| eNCF | Futuro | Fuera alcance |
| Multi-empresa | ✅ | ❌ gap |

**Ventaja competitiva Justech:** NCF operativo + reportes.  
**Gap vs producto:** seguridad multi-empresa, formato oficial, i18n.

---

## 8. Conclusión producto

El desarrollo tiene **fundamentos de producto** (arquitectura modular, naming, separación concerns) pero **presentación y hardening son de proyecto cliente**.

**Producto comercial:** **NO** (aún)  
**Potencial comercial:** **ALTO** tras sprint productización P0-P1

---

## 9. Roadmap mínimo a "SÍ comercial"

1. Hardening P0 (rules, lock, void security) — 1 sprint
2. Productización branding + i18n — 1 sprint  
3. DGII TXT reportes — fase dedicada
4. Beta con 2da empresa RD distinta a Hellenia — validación reutilización
