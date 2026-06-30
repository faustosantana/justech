# hellenia-odoo — Repositorio Git

Contenido versionado del proyecto Odoo Hellenia.

## Estructura

```
repository/
├── addons/          # Módulos custom Odoo
├── docker/
│   ├── dev/
│   └── test/
├── config/
│   ├── dev/
│   └── test/
├── scripts/
└── docs/
```

## Conectar GitHub

```bash
git remote add origin git@github.com:ORG/hellenia-odoo.git
git push -u origin main
git push -u origin develop
git push -u origin test
```

**Nunca** commitear archivos `.env` con contraseñas reales.
