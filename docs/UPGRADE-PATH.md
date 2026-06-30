# Ruta de actualización — Odoo 19 → 20 → 21+

**Principio:** La infraestructura Docker, volúmenes y separación de capas **no se rehace** en cada versión mayor. Solo se actualizan tres componentes.

---

## Componentes actualizables (sin rehacer infraestructura)

| Componente | Ubicación | Método de actualización |
|------------|-----------|-------------------------|
| **Community** | Imagen Docker | Cambiar tag pinneado en `docker-compose.yml` |
| **Enterprise** | `/opt/odoo-projects/hellenia/enterprise/` | `git pull` **o** nuevo tarball portal + `extract-enterprise-portal.sh` |
| **Custom** | `/opt/odoo-projects/hellenia/custom/` | `git pull` repo Justech |

### Lo que NO cambia entre versiones

```
/opt/odoo-projects/hellenia/
├── docker/           # Misma estructura compose; solo tag imagen
├── config/           # Mismos paths addons_path; ajustes menores si release notes
├── scripts/          # Mismos scripts; parámetros de versión
├── community/        # README de referencia
├── custom/           # Módulos propios (actualizar __manifest__.py version)
└── enterprise/       # Mismo directorio; nueva rama Git
```

---

## Procedimiento oficial de actualización (referencia)

### Imagen Docker Community

Fuente: [Docker Hub — How to upgrade](https://hub.docker.com/_/odoo)

> *"Odoo images are updated on a regular basis... upgrading from a major version to another is a much more complex process requiring elaborated migration scripts."*

Pasos documentados para **misma versión mayor** (parches):

1. Detener contenedor actual
2. Pull nueva imagen con tag pinneado
3. Recrear contenedor con mismos volúmenes
4. Aplicar `-u` solo si release notes lo indican

Para **cambio de versión mayor** (19 → 20):

1. Consultar [Odoo Upgrade](https://www.odoo.com/documentation/19.0/administration/upgrade.html)
2. Actualizar imagen Community al nuevo tag fijo
3. Actualizar rama Enterprise (`20.0`, `21.0`, etc.)
4. Ejecutar migración de BD según documentación oficial
5. Neutralizar BD de test antes de validar

### Enterprise Git (cuando esté disponible)

```bash
cd /opt/odoo-projects/hellenia/enterprise
git fetch origin 19.0
git checkout 20.0          # ejemplo Odoo 20
git pull origin 20.0
```

### Enterprise portal (parche / actualización)

1. Descargar nuevo Sources desde [odoo.com/page/download](https://www.odoo.com/page/download)
2. `scripts/extract-enterprise-portal.sh <nuevo.tar.gz>`
3. Reiniciar Odoo DEV/TEST

### Custom addons

```bash
cd /opt/odoo-projects/hellenia/repository
git pull origin <rama>
rsync -av custom/ ../custom/
# Actualizar depends y version en __manifest__.py según release notes Odoo
```

---

## Secuencia de upgrade por ambiente (permanente DEV → TEST → PROD)

```
1. Backup DEV
2. Upgrade imagen + enterprise + custom en DEV
3. Migrar BD hellenia_dev (odoo-bin upgrade o servicio Odoo Upgrade)
4. Validar DEV
5. Duplicar DEV → TEST (neutralize) — método oficial
6. Validar TEST (UAT)
7. Backup PROD
8. Upgrade PROD (ventana de mantenimiento)
9. Refrescar DEV/TEST como duplicados neutralizados de PROD
```

---

## Cambios mínimos por versión mayor

### docker-compose.yml (DEV y TEST)

```yaml
# Antes (Odoo 19)
image: odoo:19.0-20260619

# Después (Odoo 20 — ejemplo; usar tag fijo real cuando exista)
image: odoo:20.0-YYYYMMDD
```

### clone-enterprise.sh / enterprise/

```bash
BRANCH="20.0"   # alinear con versión mayor Community
```

### config/*/odoo.conf

Sin cambio estructural. Verificar si release notes modifican `addons_path` o parámetros nuevos.

---

## Checklist pre-upgrade (cualquier versión)

| # | Verificación |
|---|--------------|
| 1 | Backup completo BD + filestore (DEV/TEST/PROD según alcance) |
| 2 | Leer release notes Odoo N y N-1 |
| 3 | Verificar módulos custom compatibles (`depends`, APIs deprecadas) |
| 4 | Tag Docker pinneado (nunca `latest`) |
| 5 | Rama Enterprise alineada |
| 6 | Suscripción activa (In Progress) |
| 7 | Conectividad `services.odoo.com:80` |
| 8 | BD de prueba neutralizada para validación |
| 9 | Producción legacy (`odoo-pecv`) no afectada hasta migración planificada |

---

## Versiones objetivo

| Versión | Community | Enterprise branch | Estado |
|---------|-----------|-------------------|--------|
| **19** (actual) | `odoo:19.0-20260619` | `19.0` | Activo DEV/TEST |
| **20** | `odoo:20.0-<tag>` | `20.0` | Futuro — mismo procedimiento |
| **21** | `odoo:21.0-<tag>` | `21.0` | Futuro — mismo procedimiento |

---

## Referencias

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md)
- [GIT-STRATEGY.md](GIT-STRATEGY.md)
- [Odoo Upgrade documentation](https://www.odoo.com/documentation/19.0/administration/upgrade.html)
