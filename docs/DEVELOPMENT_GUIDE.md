# Guía de desarrollo — Hellenia Odoo

**Audiencia:** Desarrolladores Justech  
**Horizonte:** Implementación mantenible 10+ años

---

## Principios

1. **Herencia, nunca parche** — Personalizar vía `_inherit`, no editar Community ni Enterprise
2. **Módulos pequeños y cohesivos** — Un dominio por módulo (`hellenia_inventory`, no un mega-módulo)
3. **Versionado semántico Odoo** — `19.0.X.Y.Z` en `__manifest__.py`
4. **Scripts para todo** — Despliegues, backups y upgrades nunca manuales ad-hoc
5. **Documentación junto al código** — README por módulo + guías en `docs/`

---

## Estructura del proyecto

```
hellenia/
├── docker/           # INFRAESTRUCTURA — Compose, redes, volúmenes
├── config/           # CONFIGURACIÓN — odoo.conf, .env por ambiente
├── data/             # DATOS INICIALES — CSV/XML transversales (no por módulo)
├── custom/           # MÓDULOS — único código propio
├── community/        # Referencia Community (imagen Docker)
├── enterprise/       # Clone Git Odoo (no en Justech Git)
├── scripts/          # AUTOMATIZACIÓN — deploy, backup, upgrade
├── docs/             # DOCUMENTACIÓN
├── backups/          # Operativo (gitignored)
└── logs/             # Operativo (gitignored)
```

Ver [ARCHITECTURE.md](ARCHITECTURE.md) y [INFRASTRUCTURE_REVIEW.md](INFRASTRUCTURE_REVIEW.md).

---

## Flujo de trabajo diario

### 1. Desarrollo local / Cursor

```bash
git checkout -b feature/hellenia-mi-cambio
# Editar custom/hellenia_*/
git commit -m "feat(hellenia_inventory): descripción"
git push origin feature/hellenia-mi-cambio
# PR → hellenia-odoo-infra
```

### 2. Despliegue DEV

```bash
/opt/odoo-projects/hellenia/scripts/deploy-dev.sh hellenia-odoo-infra
```

Sincroniza: `custom/`, `docker/`, `config/` (sin `.env`), `scripts/`, `data/`.

### 3. Actualizar módulo en BD

```bash
/opt/odoo-projects/hellenia/scripts/update-custom-modules.sh dev hellenia_inventory
```

### 4. Validación

```bash
/opt/odoo-projects/hellenia/scripts/healthcheck.sh
/opt/odoo-projects/hellenia/scripts/validate-odoo19.sh dev
```

---

## Entornos

| Ambiente | Rama Git típica | URL |
|----------|-----------------|-----|
| DEV | `hellenia-odoo-infra` / `feature/*` | dev.hellenia.cloud |
| TEST | `hellenia-odoo-infra` (tag/commit aprobado) | test.hellenia.cloud |
| PROD | `main` (futuro) | odoo.hellenia.cloud |

---

## Herramientas de calidad (estrategia — no implementadas aún)

Análisis de conveniencia para incorporar en fase post-E1:

### Recomendación Justech

| Herramienta | ¿Incorporar? | Rol |
|-------------|--------------|-----|
| **pre-commit** | ✅ Sí (fase 2) | Orquestador de hooks antes de commit |
| **Ruff** | ✅ Sí (preferido) | Lint + format Python rápido; reemplaza flake8+isort parcialmente |
| **black** | ⚠️ Opcional | Si Ruff format no basta; elegir uno, no ambos |
| **isort** | ⚠️ Con Ruff | Ruff incluye ordenación imports; isort redundante si se usa Ruff |
| **pylint-odoo** | ✅ Sí | Reglas específicas Odoo (manifest, XML, deprecated APIs) |
| **pytest** | ✅ Sí | Runner tests; integrar con `odoo-bin` test tags |
| **GitHub Actions** | ✅ Sí (fase 2) | CI en PRs: lint + tests custom |

### Pipeline CI propuesto (futuro)

```yaml
# .github/workflows/custom-quality.yml (NO crear aún)
on: [pull_request]
jobs:
  lint:
  - ruff check custom/
  - pylint-odoo custom/
  test:
  - # Odoo test runner en contenedor DEV (self-hosted o service)
```

### Por qué no implementar ahora

- E1 aún no activó Enterprise
- Módulos custom son esqueletos sin lógica
- Evitar configurar CI antes de congelar arquitectura

**Cuándo implementar:** Tras E1a exitoso y primer módulo con modelos reales.

### Archivos futuros (referencia)

```
.pre-commit-config.yaml
pyproject.toml          # Ruff config
.odoo-lint.yml          # pylint-odoo
.github/workflows/
```

---

## Referencias

- [CODING_STANDARDS.md](CODING_STANDARDS.md)
- [CUSTOM_MODULE_GUIDE.md](CUSTOM_MODULE_GUIDE.md)
- [DEVOPS_GUIDE.md](DEVOPS_GUIDE.md)
- [UPGRADE_POLICY.md](UPGRADE_POLICY.md)
