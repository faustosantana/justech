# Herramientas de calidad — Estrategia (no implementadas)

**Estado:** Documentado — implementar post-E1  
**Guía principal:** [DEVELOPMENT_GUIDE.md](../docs/DEVELOPMENT_GUIDE.md)

## Stack recomendado

```
pre-commit → Ruff (lint+format) + pylint-odoo + pytest
GitHub Actions → CI en pull requests
```

## Archivos futuros

```
.pre-commit-config.yaml
pyproject.toml
.github/workflows/custom-quality.yml
```

No crear hasta primer módulo con lógica de negocio.
