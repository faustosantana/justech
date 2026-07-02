# Política de actualización — Hellenia Odoo

**Horizonte:** 10+ años  
**Complementa:** [UPGRADE-PATH.md](UPGRADE-PATH.md) (procedimiento técnico)

---

## Alcance de una actualización

Una actualización de versión Odoo **solo** modifica:

| Componente | Acción |
|------------|--------|
| Community | Nuevo tag imagen Docker |
| Enterprise | Nueva rama Git (`20.0`, `21.0`, …) |
| Custom | Ajustes compatibilidad en `custom/` |
| Infraestructura | **Sin cambios estructurales** salvo release notes |

**No se rehace:** docker compose layout, separación capas, scripts base, Traefik.

---

## Tipos de actualización

| Tipo | Frecuencia | Ejemplo |
|------|------------|---------|
| **Parche** | Mensual o según CVE | `19.0-20260619` → `19.0-20260715` |
| **Menor** | Según Odoo | 19.0 → 19.3 |
| **Mayor** | Planificado | 19 → 20 → 21 |

---

## Gobernanza

### Quién aprueba

| Actualización | Aprobador |
|---------------|-----------|
| Parche seguridad DEV | Justech (autónomo) |
| Parche TEST | Justech + notificación Hellenia |
| Parche PROD | Hellenia + ventana mantenimiento |
| Versión mayor | Hellenia + plan migración documentado |

### Secuencia obligatoria

```
DEV (upgrade + validar)
  → TEST (duplicar DEV neutralizado o upgrade directo)
    → UAT Hellenia
      → PROD (ventana mantenimiento)
        → Refrescar DEV/TEST desde PROD neutralizado
```

---

## Pre-requisitos (checklist)

- [ ] Suscripción Enterprise activa (**In Progress**)
- [ ] Backup completo BD + filestore
- [ ] Release notes Odoo leídas
- [ ] Módulos custom revisados (APIs deprecadas)
- [ ] Tag Docker **pinneado** (nunca `latest`)
- [ ] Rama Enterprise alineada con versión mayor
- [ ] `services.odoo.com:80` accesible
- [ ] Plan rollback documentado

---

## Procedimiento por componente

### Community

```bash
# 1. Commit nuevo tag en docker-compose.yml
# 2. Ejecutar:
scripts/upgrade-community.sh dev
scripts/validate-odoo19.sh dev
```

### Enterprise

```bash
scripts/upgrade-enterprise.sh 19.0   # o 20.0 en futuro
```

### Custom

```bash
# Ajustar código + manifest version
scripts/deploy-dev.sh
scripts/update-custom-modules.sh dev <modulos>
```

### Base de datos (versión mayor)

Seguir [documentación oficial Odoo Upgrade](https://www.odoo.com/documentation/19.0/administration/upgrade.html):

- BD de prueba **neutralizada** antes de validar
- Nunca upgrade directo en PROD sin UAT en TEST

---

## Licenciamiento en upgrades

- Una BD vinculada al código de suscripción
- Ambientes de prueba: duplicación + neutralize ([ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md))
- Tras upgrade mayor en PROD: refrescar DEV/TEST como duplicados neutralizados

---

## Rollback

| Escenario | Acción |
|-----------|--------|
| Fallo en DEV | `restore-dev.sh <backup-pre-upgrade>` |
| Fallo en TEST | `restore-test.sh <backup-pre-upgrade>` |
| Fallo en PROD | Restaurar backup + imagen anterior; ticket soporte Odoo si migración BD parcial |

Ver [ROLLBACK.md](ROLLBACK.md) y [DEVOPS_GUIDE.md](DEVOPS_GUIDE.md).

---

## Calendario sugerido (referencia)

| Actividad | Frecuencia |
|-----------|------------|
| Revisar tags Docker Odoo | Mensual |
| `git fetch` Enterprise | Mensual |
| Backup verificado (restore test) | Trimestral |
| Upgrade parche DEV | Según release |
| Upgrade mayor | Según roadmap Odoo + Hellenia |

---

## Versiones en roadmap

| Versión | Estado | Rama Enterprise | Imagen Community |
|---------|--------|-----------------|------------------|
| 19.0 | Activo DEV/TEST | `19.0` | `19.0-20260619` |
| 20.0 | Futuro | `20.0` | `20.0-<tag>` |
| 21.0 | Futuro | `21.0` | `21.0-<tag>` |

---

## Referencias

- [UPGRADE-PATH.md](UPGRADE-PATH.md)
- [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md)
- [DEVOPS_GUIDE.md](DEVOPS_GUIDE.md)
