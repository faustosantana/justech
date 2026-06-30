# Fase E1 — Validación final pre-ejecución

**Estado:** Pendiente de aprobación — **NO ejecutar hasta autorización explícita**  
**Alcance E1a:** Solo ambiente **DEV** (`hellenia_dev` / `dev.hellenia.cloud`)  
**Prerrequisito:** Fases E0.5–E0.9 completadas y documentación revisada ✅

---

## Revisión del procedimiento oficial Enterprise

Este checklist consolida el procedimiento documentado por Odoo para on-premise Docker + Enterprise Git.

### Fuentes oficiales verificadas

| # | Documento oficial | Contenido aplicado |
|---|-------------------|-------------------|
| 1 | [Source install — Git](https://www.odoo.com/documentation/19.0/administration/on_premise/source.html) | Clone `odoo/enterprise` rama `19.0`; Enterprise antes de Community en `addons_path` |
| 2 | [Community → Enterprise](https://www.odoo.com/documentation/19.0/administration/on_premise/community_to_enterprise.html) | Backup → `addons_path` → `-i web_enterprise` → reiniciar → registrar código |
| 3 | [On-premise](https://www.odoo.com/documentation/19.0/administration/on_premise.html) | Registro suscripción; duplicación para test/dev |
| 4 | [Docker Hub odoo](https://hub.docker.com/_/odoo) | Sin imagen Enterprise; montar volumen; múltiples instancias permitidas |
| 5 | [Neutralized database](https://www.odoo.com/documentation/19.0/administration/neutralized_database.html) | TEST futuro por duplicación neutralizada |

### Secuencia oficial (mejor práctica confirmada)

```
1. Obtener Enterprise vía Git (rama = versión mayor Community)
2. Montar enterprise/ como volumen read-only en Docker
3. addons_path: enterprise PRIMERO, luego Community, luego custom
4. Backup BD
5. odoo -i web_enterprise --stop-after-init
6. Reiniciar y verificar UI Enterprise
7. Registrar subscription code en banner (E1b — aprobación separada)
```

> **Mejora respecto a versión anterior:** Autenticación Git por **SSH key dedicada** en lugar de PAT permanente en `github.env`. Ver [E0.6-GITHUB-ENTERPRISE.md](E0.6-GITHUB-ENTERPRISE.md).

---

## Principios de ejecución

| Regla | Responsable |
|-------|-------------|
| Vincular usuario GitHub en portal Odoo | **Usuario** (único paso manual en portal) |
| Agregar SSH public key en GitHub | **Usuario** (copiar `.pub` generada por Cursor) |
| Generar clave SSH, `ssh_config`, clonar, validar | **Cursor** vía SSH |
| Editar archivos manualmente en VPS | **Nadie** |
| Wizard, usuarios, l10n_do, licencia UI | **Bloqueado** en E1a |
| Producción `odoo-pecv` | **No tocar** |

---

## Parte A — Acceso GitHub (antes de E1)

### A.1 Portal Odoo (manual — usuario)

| # | Acción |
|---|--------|
| 1 | [odoo.com/my/subscriptions](https://www.odoo.com/my/subscriptions) → `M260616306091776` |
| 2 | **GitHub Users** → agregar username exacto |
| 3 | Esperar 5–30 min |
| 4 | Verificar [github.com/odoo/enterprise](https://github.com/odoo/enterprise) visible |
| 5 | Verificar rama **`19.0`** existe |

### A.2 SSH Key en GitHub (preferido)

| # | Acción | Quién |
|---|--------|-------|
| 1 | Cursor genera `github_ed25519` + `github_ed25519.pub` en VPS | Cursor |
| 2 | Usuario copia contenido de `.pub` → GitHub → Settings → SSH and GPG keys | Usuario |
| 3 | Cursor verifica `git ls-remote` con `ssh_config` | Cursor |

**No se almacena PAT** si SSH funciona.

### A.3 Fallback PAT (solo si SSH falla)

Fine-grained PAT, Contents Read-only, repo `odoo/enterprise`. Temporal; migrar a SSH cuando sea posible.

---

## Parte B — Checklist pre-vuelo (Cursor vía SSH)

| # | Verificación | Comando / script |
|---|--------------|------------------|
| B1 | Arquitectura E0.9 | `community/`, `enterprise/`, `custom/hellenia_*` |
| B2 | Red saliente Odoo | `scripts/validate-subscription-env.sh` |
| B3 | Backup DEV | `scripts/backup-dev.sh` |
| B4 | DEV HTTP 200 | `curl -sS -o /dev/null -w '%{http_code}' https://dev.hellenia.cloud/web/login` |
| B5 | Producción intacta | `docker ps --filter name=odoo-pecv` |
| B6 | SSH key + ssh_config | Existen en `config/credentials/`, chmod correcto |
| B7 | Acceso GitHub dry-run | `git ls-remote git@github.com:odoo/enterprise.git refs/heads/19.0` |

**Comando B7:**

```bash
GIT_SSH_COMMAND="ssh -F /opt/odoo-projects/hellenia/config/credentials/ssh_config" \
  git ls-remote git@github.com:odoo/enterprise.git refs/heads/19.0
```

---

## Parte C — Comandos E1a (Cursor ejecuta tras aprobación)

### C.1 Configurar SSH (Cursor)

```bash
install -d -m 700 /opt/odoo-projects/hellenia/config/credentials
ssh-keygen -t ed25519 -C "hellenia-vps-enterprise" \
  -f /opt/odoo-projects/hellenia/config/credentials/github_ed25519 -N ""
chmod 600 /opt/odoo-projects/hellenia/config/credentials/github_ed25519
chmod 644 /opt/odoo-projects/hellenia/config/credentials/github_ed25519.pub

cat > /opt/odoo-projects/hellenia/config/credentials/ssh_config << 'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile /opt/odoo-projects/hellenia/config/credentials/github_ed25519
  IdentitiesOnly yes
EOF
chmod 600 /opt/odoo-projects/hellenia/config/credentials/ssh_config
```

> **Pausa:** Usuario agrega `.pub` en GitHub. Cursor continúa tras confirmación.

### C.2 Sincronizar infra desde Git

```bash
cd /opt/odoo-projects/hellenia/repository
git fetch origin cursor/odoo19-migration-dev-test-dd85
git pull origin cursor/odoo19-migration-dev-test-dd85
rsync -av repository/scripts/ /opt/odoo-projects/hellenia/scripts/
rsync -av repository/docker/ /opt/odoo-projects/hellenia/docker/
rsync -av repository/config/dev/odoo.conf /opt/odoo-projects/hellenia/config/dev/
rsync -av repository/custom/ /opt/odoo-projects/hellenia/custom/
chmod +x /opt/odoo-projects/hellenia/scripts/*.sh
```

### C.3 Backup pre-E1

```bash
/opt/odoo-projects/hellenia/scripts/backup-dev.sh
```

### C.4 Clonar Enterprise (Git oficial, rama 19.0)

```bash
/opt/odoo-projects/hellenia/scripts/clone-enterprise.sh
```

### C.5 Recrear contenedor DEV

```bash
cd /opt/odoo-projects/hellenia/docker/dev
docker compose --env-file ../../config/dev/.env pull odoo
docker compose --env-file ../../config/dev/.env up -d --force-recreate odoo
sleep 45
```

### C.6 Instalar `web_enterprise` (procedimiento oficial)

```bash
source /opt/odoo-projects/hellenia/config/dev/.env
cd /opt/odoo-projects/hellenia/docker/dev
docker compose --env-file ../../config/dev/.env stop odoo
docker compose --env-file ../../config/dev/.env run --rm odoo odoo \
  -d hellenia_dev --db_host=db --db_user=odoo --db_password="$DB_PASSWORD" \
  -i web_enterprise --stop-after-init
docker compose --env-file ../../config/dev/.env up -d odoo
sleep 40
```

### C.7 Validar

```bash
/opt/odoo-projects/hellenia/scripts/validate-enterprise-dev.sh
```

### C.8 Registro licencia — E1b (bloqueado en E1a)

Código `M260616306091776` en banner UI. Requiere aprobación separada.

### C.9 l10n_do — E1c (bloqueado)

---

## Parte D — Criterios de éxito E1a

| Check | Esperado |
|-------|----------|
| `enterprise/web_enterprise/__manifest__.py` | Existe |
| Rama Git | `19.0` |
| Volumen `/mnt/enterprise` | Montado en contenedor |
| `web_enterprise` en BD | `state = installed` |
| HTTP login | 200 |
| `database.enterprise_code` | Vacío (OK en E1a) |
| Producción | Intacta |

```bash
/opt/odoo-projects/hellenia/scripts/validate-enterprise-dev.sh
```

**Salida esperada:**

```
OK  enterprise montado
OK  custom montado
OK  addons_path incluye enterprise
OK  web_enterprise instalado en BD
OK  login HTTP 200
WARN database.enterprise_code vacío
OK  producción intacta
RESULTADO: OK
```

---

## Parte E — Rollback

### E.1 Antes de `web_enterprise`

```bash
rm -rf /opt/odoo-projects/hellenia/enterprise/.git
cd /opt/odoo-projects/hellenia/docker/dev
docker compose --env-file ../../config/dev/.env up -d --force-recreate odoo
```

### E.2 Después de `web_enterprise`

Restaurar backup pre-E1 desde `backups/dev/<TIMESTAMP>/`.

### E.3 Revocar acceso GitHub

```bash
rm -f /opt/odoo-projects/hellenia/config/credentials/github_ed25519*
rm -f /opt/odoo-projects/hellenia/config/credentials/ssh_config
```

Usuario elimina SSH key en GitHub → Settings → SSH keys.

---

## Parte F — Sub-fases

| Sub-fase | Contenido | Aprobación |
|----------|-----------|------------|
| **E1a** | SSH → clone Git → volúmenes → `web_enterprise` → validar | Este documento |
| **E1b** | Registrar `M260616306091776` en DEV | Separada |
| **E1c** | `l10n_do`, `l10n_do_edi`, `l10n_do_reports` | Separada |
| **E1d** | Wizard, usuarios, Infile | Fuera de alcance |

---

## Parte G — Requisitos para aprobar E1a

1. Confirmación explícita: *"Aprobado E1a"*
2. GitHub vinculado en portal Odoo (A.1)
3. Usuario disponible para agregar SSH public key cuando Cursor la genere
4. Documentación revisada:
   - [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md)
   - [ARCHITECTURE.md](ARCHITECTURE.md)
   - [E0.6-GITHUB-ENTERPRISE.md](E0.6-GITHUB-ENTERPRISE.md)
   - [UPGRADE-PATH.md](UPGRADE-PATH.md)

---

## Parte H — Referencias

| Documento | Contenido |
|-----------|-----------|
| [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md) | Política oficial licenciamiento |
| [ENTERPRISE_ANALYSIS.md](ENTERPRISE_ANALYSIS.md) | Análisis técnico Enterprise |
| [UPGRADE-PATH.md](UPGRADE-PATH.md) | Odoo 20/21+ sin rehacer infra |
| [ARCHITECTURE.md](ARCHITECTURE.md) | DEV → TEST → PROD permanente |

---

## Estado

| Item | Estado |
|------|--------|
| Revisión procedimiento oficial | ✅ Completada |
| Documentación actualizada | ✅ |
| E1a ejecutado | ⛔ Esperando aprobación |
| E1b licencia | ⛔ Bloqueado |
| E1c l10n_do | ⛔ Bloqueado |
