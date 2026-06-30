# Fase E1 — Validación final pre-ejecución

**Estado:** E1a-revised — vía **portal Odoo** (ver [ENTERPRISE_ACCESS_OPTIONS.md](ENTERPRISE_ACCESS_OPTIONS.md))  
**Alcance E1a:** Solo ambiente **DEV** (`hellenia_dev` / `dev.hellenia.cloud`)  
**Prerrequisito:** Fases E0.5–E0.9 completadas ✅

> **Cambio 2026-06-30:** GitHub bloqueado para `faustosantana`. Método principal: **descarga oficial Sources** desde portal Odoo. Ver [E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md](E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md).

---

## Revisión del procedimiento oficial Enterprise

Este checklist consolida el procedimiento documentado por Odoo para on-premise Docker + Enterprise (**Archive o Git**).

### Fuentes oficiales verificadas

| # | Documento oficial | Contenido aplicado |
|---|-------------------|-------------------|
| 1 | [Source install — Archive / Git](https://www.odoo.com/documentation/19.0/administration/on_premise/source.html) | ZIP/tarball **o** `odoo/enterprise` rama `19.0` |
| 2 | [Packaged installers](https://www.odoo.com/documentation/19.0/administration/on_premise/packages.html) | Login on-premise customer para descarga Enterprise |
| 3 | [Bugfix updates](https://www.odoo.com/documentation/19.0/administration/on_premise/update.html) | odoo.com/page/download; enlace email compra |
| 4 | [Community → Enterprise](https://www.odoo.com/documentation/19.0/administration/on_premise/community_to_enterprise.html) | `-i web_enterprise` |
| 5 | [Docker Hub odoo](https://hub.docker.com/_/odoo) | Volumen `/mnt/enterprise` |

### Secuencia E1a — vía portal (recomendada)

```
1. Usuario: descargar Sources Odoo 19 (portal) o entregar URL/archivo a Cursor
2. Cursor: download-enterprise-portal.sh | receive-enterprise-archive.sh
3. scripts/validate-enterprise-archive.sh --report
4. [Aprobación E1a] e1a-portal-pipeline.sh --execute
   → extract-enterprise-portal.sh
   → recrear contenedor DEV
   → backup-dev.sh
   → odoo -i web_enterprise --stop-after-init
   → validate-enterprise-dev.sh
```

Ver [E0.6c-ENTERPRISE-DELIVERY-FLOW.md](E0.6c-ENTERPRISE-DELIVERY-FLOW.md).

### Secuencia E1a — vía Git (alternativa)

```
fetch-enterprise.sh --git-only   # cuando GitHub accesible
```

---

## Principios de ejecución

| Regla | Responsable |
|-------|-------------|
| Descargar Sources / copiar enlace portal | **Usuario** |
| Transferir al VPS (automático vía Cursor) | **Cursor** — sin SCP del usuario |
| Validar, extract, `web_enterprise`, validar DEV | **Cursor** tras aprobación E1a |
| Wizard, usuarios, l10n_do, licencia UI | **Bloqueado** |
| TEST / PRODUCCIÓN | **No tocar** |

---

## Parte A — Acceso Enterprise (portal — preferido)

### A.1 Verificar descarga habilitada (usuario)

| # | Acción |
|---|--------|
| 1 | Login [odoo.com](https://www.odoo.com) — cuenta de `M260616306091776` |
| 2 | [odoo.com/page/download](https://www.odoo.com/page/download) |
| 3 | Odoo **19** → Enterprise → **Sources** → debe decir **Download** (no Buy) |
| 4 | Descargar archivo `.tar.gz` o `.zip` |

### A.2 Entregar a Cursor (sin SCP al VPS)

Ver [E0.6c-ENTERPRISE-DELIVERY-FLOW.md](E0.6c-ENTERPRISE-DELIVERY-FLOW.md).

| Opción | Acción usuario |
|--------|----------------|
| **A** Enlace temporal | Clic derecho → Copiar enlace en Download → pegar en Cursor |
| **B** Archivo | Adjuntar `.tar.gz` / `.zip` al chat |

### A.3 Validar archivo (Cursor — sin instalar)

```bash
/opt/odoo-projects/hellenia/scripts/e1a-portal-pipeline.sh --validate-only \
  /opt/odoo-projects/hellenia/downloads/enterprise/<archivo>.tar.gz
```

O:

```bash
/opt/odoo-projects/hellenia/scripts/validate-enterprise-archive.sh \
  /opt/odoo-projects/hellenia/downloads/enterprise/<archivo>.tar.gz --report
```

---

## Parte A-alt — GitHub (paralelo, no bloqueante)

Ver [E0.6-GITHUB-ENTERPRISE.md](E0.6-GITHUB-ENTERPRISE.md). Estado actual: SSH `faustosantana` sin acceso a `odoo/enterprise`.

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

### C.4 Obtener código Enterprise

**Portal (recomendado):**

```bash
/opt/odoo-projects/hellenia/scripts/extract-enterprise-portal.sh \
  /opt/odoo-projects/hellenia/downloads/enterprise/<archivo>.tar.gz
```

**Git (si acceso habilitado):**

```bash
/opt/odoo-projects/hellenia/scripts/fetch-enterprise.sh --git-only
```

**Auto (Git → portal):**

```bash
/opt/odoo-projects/hellenia/scripts/fetch-enterprise.sh
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
