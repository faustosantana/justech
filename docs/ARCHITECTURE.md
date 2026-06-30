# Arquitectura Odoo Enterprise — Hellenia

**Fase:** E0.7 — E0.9 (aprobada)  
**Principio:** Separación estricta Community / Enterprise / Custom  
**Pipeline permanente:** DEV → TEST → PRODUCCIÓN (toda la vida del proyecto)

---

## Pipeline de ambientes (definitivo)

```
┌──────────┐     promoción      ┌──────────┐     go-live      ┌──────────────┐
│   DEV    │ ─────────────────► │   TEST   │ ───────────────► │  PRODUCCIÓN  │
│ hellenia │   duplicar +       │ hellenia │   migración +    │  (futura)    │
│   _dev   │   neutralize       │  _test   │   registro código│              │
└──────────┘                    └──────────┘                  └──────────────┘
     ▲                               ▲                              │
     │                               │                              │
     └──────── refrescar desde PROD (duplicar + neutralize) ────────┘
```

| Ambiente | URL | BD | Rol permanente |
|----------|-----|-----|----------------|
| DEV | dev.hellenia.cloud | `hellenia_dev` | Desarrollo custom y configuración |
| TEST | test.hellenia.cloud | `hellenia_test` | UAT y validación pre-producción |
| PROD (actual) | odoo-pecv | — | Odoo 18 — **no tocar** |
| PROD (futuro) | odoo.hellenia.cloud | TBD | Operación Enterprise registrada |

**Licenciamiento:** Ver [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md). Una BD vinculada al código; ambientes adicionales por duplicación neutralizada (documentación oficial Odoo).

---

## Árbol de directorios (VPS)

```
/opt/odoo-projects/hellenia/
├── community/          # Metadatos Community (código en imagen Docker)
├── enterprise/         # Git clone odoo/enterprise @ 19.0 (NO en Git Justech)
├── custom/             # Módulos Justech — único lugar para desarrollo propio
│   ├── hellenia_base/
│   ├── hellenia_inventory/
│   ├── hellenia_reports/
│   ├── hellenia_account/
│   ├── hellenia_pos/
│   └── justech_core/
├── config/
│   ├── dev/
│   ├── test/
│   ├── production/
│   └── credentials/    # SSH keys GitHub — NUNCA en Git
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

## Separación de responsabilidades (congelada pre-E1)

| Capa | Directorio | Actualizable en upgrade Odoo |
|------|------------|------------------------------|
| Infraestructura | `docker/` | Solo tag imagen |
| Configuración | `config/` | Mínimo (release notes) |
| Datos iniciales | `data/`, `custom/*/data/` | Según módulos |
| Módulos | `custom/` | Sí — código propio |
| Enterprise | `enterprise/` | `git pull` rama mayor |
| Community | Imagen Docker | Nuevo tag |
| Scripts | `scripts/` | Evolución independiente |
| Documentación | `docs/` | Continua |

Ver [INFRASTRUCTURE_REVIEW.md](INFRASTRUCTURE_REVIEW.md).

---

## Separación de capas

| Capa | Ubicación física | Origen | Modificable |
|------|------------------|--------|-------------|
| **Enterprise** | `enterprise/` | `git clone odoo/enterprise` | ❌ Nunca |
| **Community** | Contenedor Docker | Imagen `odoo:19.0-20260619` | ❌ Nunca |
| **Custom** | `custom/` | Repo Justech | ✅ Solo aquí |

### `addons_path` (orden obligatorio)

```ini
addons_path = /mnt/enterprise,/usr/lib/python3/dist-packages/odoo/addons,/mnt/custom
```

| Orden | Path contenedor | Contenido |
|-------|-----------------|-----------|
| 1º | `/mnt/enterprise` | Módulos Enterprise |
| 2º | `/usr/lib/.../odoo/addons` | Community (imagen oficial) |
| 3º | `/mnt/custom` | Justech custom |

---

## Docker Compose — volúmenes

```yaml
volumes:
  - odoo-data:/var/lib/odoo
  - ${ENTERPRISE_PATH}:/mnt/enterprise:ro
  - ${CUSTOM_ADDONS_PATH}:/mnt/custom:ro
  - ${ODOO_CONF_PATH}:/etc/odoo/odoo.conf:ro
```

---

## Carpeta `custom/` — módulos planificados

Estructura preparada (sin desarrollo aún):

| Módulo | Propósito futuro |
|--------|------------------|
| `hellenia_base` | Configuración base Hellenia |
| `hellenia_inventory` | Extensiones inventario |
| `hellenia_reports` | Reportes propios |
| `hellenia_account` | Extensiones contabilidad |
| `hellenia_pos` | Punto de venta |
| `justech_core` | Utilidades compartidas Justech |

---

## Actualizaciones futuras (Odoo 20, 21+)

La infraestructura **no se rehace**. Solo se actualizan:

1. Tag imagen Community en `docker-compose.yml`
2. `git pull` en `enterprise/` (nueva rama mayor)
3. `git pull` + deploy de `custom/`

Detalle: [UPGRADE-PATH.md](UPGRADE-PATH.md)

---

## Flujo de despliegue

```
GitHub (justech)
    │
    ▼ git pull en repository/
/opt/odoo-projects/hellenia/repository/
    │
    ├── rsync custom/ ──► /opt/odoo-projects/hellenia/custom/
    ├── sync docker/, config/, scripts/
    │
    ▼ (independiente — SSH)
enterprise/ ◄── git pull odoo/enterprise (rama 19.0)
    │
    ▼
docker compose up -d
```

---

## Seguridad

| Recurso | Git Justech | VPS |
|---------|-------------|-----|
| `custom/` | ✅ | ✅ |
| `config/*.example` | ✅ | — |
| `config/*/.env` | ❌ | ✅ chmod 600 |
| `config/credentials/` | ❌ | ✅ chmod 700 |
| `enterprise/` | ❌ | ✅ clone local SSH |

---

## Referencias

- [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md)
- [UPGRADE-PATH.md](UPGRADE-PATH.md)
- [ENTERPRISE_ANALYSIS.md](ENTERPRISE_ANALYSIS.md)
- [GIT-STRATEGY.md](GIT-STRATEGY.md)
- [E0.6-GITHUB-ENTERPRISE.md](E0.6-GITHUB-ENTERPRISE.md)
