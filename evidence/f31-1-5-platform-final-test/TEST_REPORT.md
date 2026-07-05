# F31.1.5 — Validación Runtime TEST (FINAL)

**Fecha:** 2026-07-05  
**Entorno:** `hellenia_test` / https://test.hellenia.cloud  
**Decisión:** **PASS**

---

## Backup

| Item | Valor |
|------|-------|
| Path | `/opt/odoo-projects/hellenia/backups/test/2026-07-05_1305` |
| Verificación | ✅ PASS |

---

## Tests justech_modules — 27/27 PASS

```
0 failed, 0 error(s) of 27 tests when loading database 'hellenia_test'
justech_modules: 41 tests 2.16s 2221 queries
```

**Corrección aplicada:** `tests/test_dependencies.py` — `always_enabled: False` en módulos de prueba `dep_base_mod` / `dep_child_mod` para aislar del default `always_enabled=True` de F31.1.5 en `register_from_manifest`.

---

## Hotfixes confirmados en código local

| Archivo | Fix |
|---------|-----|
| `custom/justech_modules/hooks.py` | `pre_init_hook(cr_or_env)` → `cr = getattr(cr_or_env, "cr", cr_or_env)` |
| `custom/justech_modules/hooks.py` | Guard `information_schema.tables` antes de cleanup |
| `custom/justech_modules/models/justech_module_activation_wizard.py` | `_order = "category, module_code, line_type desc, id"` |

---

## Catálogo wizard en TEST

| Métrica | Valor |
|---------|-------|
| Módulos en wizard | **11/11** (instalados con `justech_register`) |
| Features | 11 |
| `always_enabled` | ✅ todos activos, sin bloqueo |
| Activar/desactivar + auditoría | ✅ |
| Sin install/uninstall Odoo | ✅ |

### Módulos NO instalados en TEST (documentado)

| Módulo | Estado TEST | Nota |
|--------|-------------|------|
| `justech_core` | `uninstalled` | Registrado en repo; no se instalará en esta fase |
| `hellenia_inventory` | `uninstalled` | Registrado en repo; no se instalará en esta fase |

**Registry producción completo:** 13 módulos en repo. TEST opera con 11 instalados.

---

## Validación runtime — PASS

- `API_VERSION = 1` ✅
- SDK v1 (12 métodos) ✅
- Wizard menú ✅
- Catálogo 11/11 ✅

---

## Regresión fiscal — PASS

Cotización, PDFs, exporters 606/607/623, POS — sin regresiones.

---

## Healthcheck TEST — PASS

Ver `HEALTHCHECK.json` (2026-07-05_1314)

---

## Restricciones

- ✅ PROD no tocado
- ✅ Sin commit / push
- ✅ Sin cambios lógica fiscal

---

## Artefactos

| Archivo | Descripción |
|---------|-------------|
| `TEST_RESULT.json` | Resultado consolidado |
| `f31-1-5-tests.log` | Log 27/27 PASS |
| `f31-1-5-validation.log` | Validación wizard/SDK |
| `f31-1-5-regression.log` | Regresión fiscal |
| `f31-1-5-healthcheck.log` | Healthcheck |
| `f31-1-5-install.log` | Install justech_modules |
| `MODULES_NOT_INSTALLED_TEST.md` | Documentación módulos omitidos |
