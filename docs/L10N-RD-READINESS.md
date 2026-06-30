# Preparación localización RD — sin instalar módulos

**Alcance:** Análisis y preparación documental  
**Estado:** E1c bloqueado — requiere Enterprise + licencia registrada  
**No ejecutar:** wizard, usuarios, Infile prod, instalación módulos

---

## Módulos oficiales RD (stack objetivo)

| Módulo | Origen | Edición | Fase |
|--------|--------|---------|------|
| `l10n_do` | Community (imagen Docker) | Community + EE | E1c |
| `l10n_do_edi` | Enterprise | Solo Enterprise | E1c |
| `l10n_do_reports` | Enterprise | Solo Enterprise | E1c |
| `l10n_do_check_printing` | Enterprise | Opcional | Post-E1c |

Documentación: [Dominican Republic — Odoo 19](https://www.odoo.com/documentation/19.0/applications/finance/fiscal_localizations/dominican_republic.html)

---

## Prerrequisitos antes de E1c

| # | Requisito | Estado |
|---|-----------|--------|
| 1 | E1a — `web_enterprise` instalado | ⏳ Pendiente (portal o Git) |
| 2 | E1b — Licencia `M260616306091776` registrada en DEV | ⏳ Pendiente |
| 3 | Código Enterprise en `enterprise/` | ⏳ Pendiente |
| 4 | Verificar `l10n_do_edi` en rama 19.0 / tarball | ⏳ Tras extract/clone |
| 5 | Contrato Infile (solo TEST/PROD fiscal) | 📋 Ver [INFILE-REQUIREMENTS.md](INFILE-REQUIREMENTS.md) |

---

## Orden de instalación propuesto (E1c — futuro)

```
1. l10n_do              (base RD — plan contable, impuestos, NCF)
2. account_accountant   (si no instalado — suite contable EE)
3. l10n_do_edi          (eNCF — requiere Infile en cert/prod)
4. l10n_do_reports      (reportes fiscales RD)
```

Script preparado: `validate-enterprise-dev.sh --l10n` (instala y valida — **no ejecutar ahora**)

---

## Validaciones post-instalación (checklist futuro)

| Validación | Método |
|------------|--------|
| País empresa = DO | UI / `res.company` |
| Plan contable RD cargado | Contabilidad → Configuración |
| Tipos NCF configurables | Diarios con documentos |
| `l10n_do_edi` instalado | `ir_module_module` |
| Ambiente Demo sin Infile | Solo desarrollo local |
| Sin envío DGII real en DEV | BD neutralizada cuando aplique |

---

## Dependencias externas (no Odoo)

| Servicio | Obligatorio para eNCF legal | Documento |
|----------|----------------------------|-----------|
| **Infile** | Sí (TEST/PROD) | [INFILE-REQUIREMENTS.md](INFILE-REQUIREMENTS.md) |
| **DGII** | Rangos NCF/eNCF | Trámite gubernamental |
| Odoo Enterprise activo | Sí | [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md) |

---

## Módulos custom Hellenia relacionados (futuro)

| Módulo | Rol fiscal |
|--------|------------|
| `hellenia_account` | Extensiones contables RD (herencia, no parche) |
| `hellenia_reports` | Reportes propios complementarios |

**Regla:** Nunca modificar `l10n_do*` en `enterprise/` — solo `_inherit` en `custom/`.

---

## Riesgos identificados

| Riesgo | Mitigación |
|--------|------------|
| `l10n_do_edi` ausente en tarball 19.0 | Verificar tras extract; evaluar parche Odoo 19.3 |
| Instalar l10n antes de licencia | Seguir orden E1a → E1b → E1c |
| eNCF en DEV sin neutralizar | Neutralizar o ambiente Demo Infile |
| Módulos terceros (OCA ncf) | No usar — stack oficial only |

---

## Referencias

- [ENTERPRISE_ANALYSIS.md](ENTERPRISE_ANALYSIS.md) §7
- [INFILE-REQUIREMENTS.md](INFILE-REQUIREMENTS.md)
- [E1-CHECKLIST.md](E1-CHECKLIST.md) — sub-fase E1c
