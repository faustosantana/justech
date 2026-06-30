# Estrategia Git — Hellenia Odoo Enterprise

**Fase:** E0.9  
**Principio:** Un repositorio Justech para infraestructura; Enterprise completamente aislado

---

## Repositorios

| Repositorio | Remoto | Contenido | Quién lo gestiona |
|-------------|--------|-----------|-------------------|
| **justech** (infra) | `github.com/faustosantana/justech` rama `hellenia-odoo-infra` | Docker, config templates, scripts, docs, `custom/` | Justech |
| **odoo/enterprise** | `github.com/odoo/enterprise` rama `19.0` | Módulos propietarios Odoo | Odoo S.A. (solo lectura) |
| **odoo/odoo** | Público | Community — **no clonamos**; usamos imagen Docker | Odoo S.A. |

---

## Qué SÍ va en Git Justech

```
├── custom/                 # Módulos propios Justech/Hellenia
├── community/              # Solo README (sin código)
├── config/
│   ├── dev/.env.example
│   ├── test/.env.example
│   └── credentials/*.example
├── docker/
├── scripts/
├── docs/
└── .gitignore              # excluye enterprise/, secrets, backups
```

---

## Qué NO va en Git Justech

| Path | Razón |
|------|-------|
| `enterprise/` | Código OPL-1.0 propietario Odoo |
| `config/dev/.env` | Secretos |
| `config/test/.env` | Secretos |
| `config/credentials/github.env` | PAT GitHub (fallback) |
| `config/credentials/github_ed25519` | Clave SSH privada VPS |
| `config/credentials/ssh_config` | Config SSH GitHub |
| `backups/` | Datos operativos |
| `logs/` | Datos operativos |
| `enterprise/.git/` | Repo Git separado en VPS |

---

## `.gitignore` (repo Justech)

```gitignore
enterprise/
config/credentials/
config/*/.env
backups/
logs/
__pycache__/
*.pyc
```

---

## Flujo de trabajo

### Desarrollo custom

```bash
# Local o Cursor
git checkout -b feature/hellenia-mi-modulo
# editar custom/hellenia_*/
git commit -m "feat(custom): descripción"
git push origin feature/hellenia-mi-modulo
# PR → hellenia-odoo-infra
```

### Despliegue infra en VPS

```bash
cd /opt/odoo-projects/hellenia/repository
git pull origin hellenia-odoo-infra
rsync -av custom/ ../custom/
rsync -av docker/ ../docker/
rsync -av scripts/ ../scripts/
# enterprise/ se actualiza por separado:
cd ../enterprise && git pull origin 19.0
```

### Actualización Enterprise (independiente — SSH)

```bash
cd /opt/odoo-projects/hellenia/enterprise
GIT_SSH_COMMAND="ssh -F ../config/credentials/ssh_config" git fetch origin 19.0
GIT_SSH_COMMAND="ssh -F ../config/credentials/ssh_config" git pull origin 19.0
cd ../docker/dev && docker compose restart odoo
```

---

## Ramas Justech (propuesta)

| Rama | Uso |
|------|-----|
| `hellenia-odoo-infra` | Infraestructura activa DEV/TEST |
| `main` | Producción aprobada (futuro) |
| `feature/*` | Desarrollo custom / infra |
| `hotfix/*` | Correcciones urgentes |

---

## Reglas de oro

1. **Nunca** `git add enterprise/`
2. **Nunca** modificar archivos dentro `enterprise/` — usar `custom/` con `_inherit`
3. **Nunca** commitear `.env` ni tokens
4. Enterprise se clona una vez en VPS; se actualiza con `git pull` en su propio directorio
5. Custom es la única capa versionada por Justech para lógica de negocio

---

## CI/CD futuro (referencia)

- Pipeline Justech: lint/test solo `custom/`
- Pipeline NO incluye build de Enterprise
- Imagen Docker: sigue siendo `odoo:19.0-*` oficial + volúmenes montados
