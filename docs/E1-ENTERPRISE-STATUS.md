# Estado Fase E1 — Enterprise DEV

**Fecha:** 2026-06-30  
**Estado:** Arquitectura lista — **E1 bloqueado** pendiente credenciales GitHub

---

## Completado (E0.5 – E0.9)

| Fase | Estado | Evidencia |
|------|--------|-----------|
| E0.5 Validación suscripción | ✅ Docs + checks técnicos | `validate-subscription-env.sh` OK en VPS |
| E0.6 GitHub Enterprise | ✅ Documentado | `docs/E0.6-GITHUB-ENTERPRISE.md` |
| E0.7 Arquitectura | ✅ Desplegada | `community/`, `enterprise/`, `custom/` en VPS |
| E0.8 Custom addons | ✅ Preparado | `custom/README.md`, `.gitkeep` |
| E0.9 Git strategy | ✅ Documentado | `docs/GIT-STRATEGY.md`, `.gitignore` |

### Checks técnicos VPS (2026-06-30)

```
✓ DNS services.odoo.com
✓ HTTP saliente services.odoo.com:80
✓ Directorios community/, enterprise/, custom/, config/credentials/
✓ DEV monta /mnt/enterprise y /mnt/custom
✓ DEV /web/login → 200
✓ Producción odoo-pecv intacta
```

---

## Bloqueado — acción requerida

### 1. Portal Odoo (manual)

Completar checklist en `docs/E0.5-SUBSCRIPTION-VALIDATION.md`:

- [ ] Usuarios incluidos: ___
- [ ] Fecha renovación: ___
- [ ] Tipo: Odoo Enterprise confirmado
- [ ] GitHub user vinculado a `M260616306091776`

### 2. GitHub PAT en VPS

```bash
ssh root@2.25.69.179
cp /opt/odoo-projects/hellenia/config/credentials/github.env.example \
   /opt/odoo-projects/hellenia/config/credentials/github.env
chmod 600 /opt/odoo-projects/hellenia/config/credentials/github.env
# Editar GITHUB_USER y GITHUB_TOKEN
```

### 3. Ejecutar E1

```bash
/opt/odoo-projects/hellenia/scripts/install-enterprise-dev.sh
```

### 4. Registrar suscripción (UI)

1. https://dev.hellenia.cloud
2. Login admin
3. Código: `M260616306091776`

### 5. Validar Enterprise

```bash
/opt/odoo-projects/hellenia/scripts/validate-enterprise-dev.sh
```

### 6. Localización RD (tras Enterprise + registro)

```bash
/opt/odoo-projects/hellenia/scripts/validate-enterprise-dev.sh --l10n
```

---

## No ejecutado (por diseño)

- ⛔ Wizard
- ⛔ Creación usuarios
- ⛔ Configuración Infile
- ⛔ Producción
