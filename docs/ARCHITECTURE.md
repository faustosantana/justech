# Arquitectura Odoo Enterprise — Hellenia

**Fase:** E0.7 — E0.9  
**Principio:** Separación estricta Community / Enterprise / Custom

---

## Árbol de directorios (VPS)

```
/opt/odoo-projects/hellenia/
├── community/          # Metadatos Community (código en imagen Docker)
├── enterprise/         # Git clone independiente odoo/enterprise @ 19.0 (NO en Git Justech)
├── custom/             # Módulos Justech — único lugar para desarrollo propio
├── config/
│   ├── dev/
│   ├── test/
│   ├── production/
│   └── credentials/    # github.env, etc. — NUNCA en Git
├── docker/
│   ├── dev/
│   └── test/
├── scripts/
├── backups/
├── logs/
├── docs/
└── repository/         # Clone Git Justech (infra + custom)
```

---

## Separación de capas

| Capa | Ubicación física | Origen | Modificable |
|------|------------------|--------|-------------|
| **Enterprise** | `enterprise/` | `git clone odoo/enterprise` | ❌ Nunca |
| **Community** | Contenedor Docker | Imagen `odoo:19.0-20260619` | ❌ Nunca |
| **Custom** | `custom/` | Repo Justech | ✅ Solo aquí |

### `addons_path` (orden obligatorio)

```ini
# config/dev/odoo.conf y config/test/odoo.conf
addons_path = /mnt/enterprise,/usr/lib/python3/dist-packages/odoo/addons,/mnt/custom
```

| Orden | Path contenedor | Contenido |
|-------|-----------------|-----------|
| 1º | `/mnt/enterprise` | Módulos Enterprise (override) |
| 2º | `/usr/lib/.../odoo/addons` | Community (imagen oficial) |
| 3º | `/mnt/custom` | Justech custom |

> **Nunca** incluir rutas adicionales mezcladas. **Nunca** copiar módulos Enterprise o Community dentro de `custom/`.

---

## Docker Compose — volúmenes

```yaml
volumes:
  - odoo-data:/var/lib/odoo
  - ${ENTERPRISE_PATH}:/mnt/enterprise:ro
  - ${CUSTOM_ADDONS_PATH}:/mnt/custom:ro
  - ${ODOO_CONF_PATH}:/etc/odoo/odoo.conf:ro
```

Variables `.env`:

```ini
ENTERPRISE_PATH=/opt/odoo-projects/hellenia/enterprise
CUSTOM_ADDONS_PATH=/opt/odoo-projects/hellenia/custom
```

---

## Carpeta `community/`

No contiene código fuente duplicado. Incluye:

- `README.md` — documenta que Community proviene de la imagen Docker pinneada
- Referencia de versión: `odoo:19.0-20260619`
- Path interno contenedor: `/usr/lib/python3/dist-packages/odoo/addons`

Duplicar el repo `odoo/odoo` en disco **no es necesario** cuando se usa la imagen oficial Docker.

---

## Carpeta `enterprise/`

- Repositorio Git **independiente** (`odoo/enterprise`)
- Listado en `.gitignore` del repo Justech
- Clonado por `scripts/clone-enterprise.sh`
- Actualizado por `git pull` en `enterprise/`
- Montado **read-only** en contenedor

---

## Carpeta `custom/` (E0.8)

Único destino para desarrollo Justech:

```
custom/
├── README.md
└── <modulo_justech>/
    ├── __manifest__.py
    ├── models/
    ├── views/
    └── security/
```

**Reglas:**
- Heredar (`_inherit`) — no modificar archivos Enterprise/Community
- Prefijo recomendado: `justech_` o `hellenia_`
- Licencia: definir en `__manifest__.py`
- Versionado: solo en repo Justech

---

## Flujo de despliegue

```
GitHub (justech/hellenia-odoo-infra)
    │
    ▼ git pull en repository/
/opt/odoo-projects/hellenia/repository/
    │
    ├── rsync custom/ ──► /opt/odoo-projects/hellenia/custom/
    ├── sync docker/, config/, scripts/
    │
    ▼ (independiente)
enterprise/ ◄── git pull odoo/enterprise
    │
    ▼
docker compose up -d
```

---

## Ambientes

| Ambiente | URL | BD | Enterprise |
|----------|-----|-----|------------|
| DEV | dev.hellenia.cloud | hellenia_dev | E1: primera activación |
| TEST | test.hellenia.cloud | hellenia_test | Duplicado neutralizado (futuro) |
| PROD | odoo-pecv (actual) | — | Odoo 18 — sin tocar |

---

## Seguridad

| Recurso | Git Justech | VPS |
|---------|-------------|-----|
| `custom/` | ✅ | ✅ |
| `config/*.example` | ✅ | — |
| `config/*/.env` | ❌ | ✅ chmod 600 |
| `config/credentials/` | ❌ | ✅ chmod 600 |
| `enterprise/` | ❌ | ✅ clone local |

---

## Referencias

- [ENTERPRISE_ANALYSIS.md](ENTERPRISE_ANALYSIS.md)
- [GIT-STRATEGY.md](GIT-STRATEGY.md)
- [E0.5-SUBSCRIPTION-VALIDATION.md](E0.5-SUBSCRIPTION-VALIDATION.md)
- [E0.6-GITHUB-ENTERPRISE.md](E0.6-GITHUB-ENTERPRISE.md)
