# Fase E1 — Checklist de activación Enterprise (DEV)

**Estado:** Pendiente de aprobación — **NO ejecutar hasta autorización explícita**  
**Alcance:** Solo ambiente **DEV** (`hellenia_dev` / `dev.hellenia.cloud`)  
**Prerrequisito:** Fases E0.5–E0.9 completadas ✅

---

## Principios de ejecución (acordados)

| Regla | Responsable |
|-------|-------------|
| Vincular usuario GitHub en portal Odoo | **Usuario** (único paso manual inevitable) |
| Crear PAT en GitHub | **Usuario** (una vez; no se almacena en Git) |
| Entregar PAT a Cursor en sesión aprobada | **Usuario** (mensaje seguro; no commitear) |
| Escribir `github.env` en VPS vía SSH | **Cursor** (chmod 600; nunca en repo Git) |
| Clonar Enterprise, configurar, validar, revertir | **Cursor** vía SSH |
| Editar archivos manualmente en VPS | **Nadie** — automatizado por scripts |
| Wizard, usuarios, l10n_do, licencia UI, producción | **Bloqueado** en E1 inicial |

> Cuando E1 sea aprobado, el usuario **no** editará `github.env` manualmente. Cursor lo creará en el VPS con el PAT proporcionado en esa sesión.

---

## Parte A — Acceso GitHub (antes de E1)

### A.1 Vincular GitHub en portal Odoo (manual — usuario)

| # | Acción | Dónde |
|---|--------|-------|
| 1 | Iniciar sesión | [https://www.odoo.com/my/subscriptions](https://www.odoo.com/my/subscriptions) |
| 2 | Abrir suscripción | `M260616306091776` |
| 3 | Sección **GitHub Users** | Agregar username exacto de GitHub |
| 4 | Guardar | Esperar 5–30 minutos |
| 5 | Verificar en navegador | [https://github.com/odoo/enterprise](https://github.com/odoo/enterprise) — debe ser visible (no 404) |
| 6 | Verificar rama | Selector de ramas → existe **`19.0`** |

**Criterio de éxito A.1:** Repositorio `odoo/enterprise` visible con rama `19.0`.

---

### A.2 Crear Personal Access Token (manual — usuario, una sola vez)

#### ¿Fine-grained o Classic?

| Tipo | ¿Válido? | Recomendación |
|------|----------|---------------|
| **Fine-grained PAT** | ✅ Sí | **Preferido** — mínimo privilegio |
| **Classic PAT** | ✅ Sí | Alternativa si fine-grained no lista el repo |

#### Permisos requeridos

**Fine-grained PAT:**

| Campo | Valor |
|-------|-------|
| Resource owner | Tu cuenta GitHub (la vinculada en Odoo) |
| Repository access | **Only select repositories** → `odoo/enterprise` |
| Permissions → Repository contents | **Read-only** |
| Permissions → Metadata | **Read-only** (incluido por defecto) |
| Expiration | 90 días o según política Justech (renovable) |

**Classic PAT (si fine-grained no funciona):**

| Scope | Necesario |
|-------|-----------|
| `repo` | ✅ Sí (acceso a repos privados) |

> **Read-only es suficiente.** E1 solo clona (`git clone` / `git pull`). No se hace push ni fork.

#### Repositorio exacto

```
https://github.com/odoo/enterprise.git
Rama: 19.0
```

No se requiere acceso a `odoo/odoo` (Community viene de la imagen Docker).

#### Qué NO hacer con el PAT

- ❌ No commitear en repo Justech
- ❌ No pegar en `github.env.example`
- ❌ No publicar en chat permanente / tickets públicos
- ✅ Entregar solo a Cursor en sesión E1 aprobada (mensaje directo)

---

### A.3 Dónde se guardará el PAT (Cursor vía SSH)

| Ubicación | Propósito |
|-----------|-----------|
| **VPS:** `/opt/odoo-projects/hellenia/config/credentials/github.env` | Uso operativo `git clone` |
| Permisos | `chmod 600` (solo root) |
| Directorio | `chmod 700` en `config/credentials/` |
| **Git Justech** | ❌ Nunca — listado en `.gitignore` |

**Contenido que Cursor escribirá automáticamente** (sin intervención manual del usuario):

```ini
GITHUB_USER=<username-github-vinculado-en-odoo>
GITHUB_TOKEN=<pat-proporcionado-en-sesion-e1>
```

Plantilla de referencia (solo documentación): `config/credentials/github.env.example`

---

## Parte B — Checklist pre-vuelo (Cursor valida vía SSH)

Ejecutar **antes** de clonar Enterprise:

| # | Verificación | Comando / script |
|---|--------------|------------------|
| B1 | Arquitectura E0.9 | Directorios `community/`, `enterprise/`, `custom/` |
| B2 | Red saliente Odoo | `scripts/validate-subscription-env.sh` |
| B3 | Backup DEV reciente | `scripts/backup-dev.sh` |
| B4 | DEV responde | `curl -sS -o /dev/null -w '%{http_code}' https://dev.hellenia.cloud/web/login` → 200 |
| B5 | Producción intacta | `docker ps --filter name=odoo-pecv` → Up |
| B6 | `github.env` creado por Cursor | Existe, chmod 600, no en Git |
| B7 | Acceso GitHub (dry-run) | `git ls-remote` al repo enterprise rama 19.0 |

**Comando dry-run B7** (Cursor ejecutará, no clona aún):

```bash
source /opt/odoo-projects/hellenia/config/credentials/github.env
git ls-remote "https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/odoo/enterprise.git" refs/heads/19.0
```

**Criterio de éxito B7:** Hash de commit visible, sin error 401/404.

---

## Parte C — Comandos exactos que ejecutará Cursor (E1 aprobado)

> Secuencia automatizada. El usuario **no** ejecuta estos comandos.

### C.1 Crear credenciales (Cursor vía SSH)

```bash
install -d -m 700 /opt/odoo-projects/hellenia/config/credentials
cat > /opt/odoo-projects/hellenia/config/credentials/github.env << 'EOF'
GITHUB_USER=<username>
GITHUB_TOKEN=<pat>
EOF
chmod 600 /opt/odoo-projects/hellenia/config/credentials/github.env
```

### C.2 Sincronizar infra desde Git

```bash
cd /opt/odoo-projects/hellenia/repository
git fetch origin cursor/odoo19-migration-dev-test-dd85
git pull origin cursor/odoo19-migration-dev-test-dd85
rsync -av repository/scripts/ /opt/odoo-projects/hellenia/scripts/
rsync -av repository/docker/ /opt/odoo-projects/hellenia/docker/
rsync -av repository/config/dev/odoo.conf /opt/odoo-projects/hellenia/config/dev/
chmod +x /opt/odoo-projects/hellenia/scripts/*.sh
```

### C.3 Backup pre-E1

```bash
/opt/odoo-projects/hellenia/scripts/backup-dev.sh
```

### C.4 Clonar Enterprise (rama 19.0)

```bash
/opt/odoo-projects/hellenia/scripts/clone-enterprise.sh
```

Equivalente interno:

```bash
git clone "https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/odoo/enterprise.git" \
  --branch 19.0 --depth 1 /opt/odoo-projects/hellenia/enterprise
```

### C.5 Recrear contenedor DEV con volúmenes Enterprise

```bash
cd /opt/odoo-projects/hellenia/docker/dev
docker compose --env-file ../../config/dev/.env pull odoo
docker compose --env-file ../../config/dev/.env up -d --force-recreate odoo
sleep 45
```

### C.6 Instalar `web_enterprise` en BD

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

### C.7 Validar carga Enterprise (sin registrar licencia aún)

```bash
/opt/odoo-projects/hellenia/scripts/validate-enterprise-dev.sh
```

### C.8 Registrar licencia (solo si aprobado en sub-paso E1b)

> **Fuera del alcance de E1 inicial** salvo aprobación explícita adicional.

1. Usuario abre `https://dev.hellenia.cloud`
2. Login admin existente
3. Ingresa `M260616306091776` en banner
4. Cursor verifica:

```bash
docker exec hellenia-dev-db-1 psql -U odoo -d hellenia_dev -tAc \
  "SELECT value FROM ir_config_parameter WHERE key='database.enterprise_code';"
```

### C.9 Localización RD (solo fase E1c — NO en E1 inicial)

> **Bloqueado** hasta aprobación separada:

```bash
/opt/odoo-projects/hellenia/scripts/validate-enterprise-dev.sh --l10n
```

---

## Parte D — Cómo validar que Enterprise quedó cargado

### D.1 Filesystem (VPS)

| Check | Comando | Esperado |
|-------|---------|----------|
| Repo clonado | `test -f /opt/odoo-projects/hellenia/enterprise/web_enterprise/__manifest__.py` | exit 0 |
| Rama correcta | `git -C /opt/odoo-projects/hellenia/enterprise branch --show-current` | `19.0` |
| Módulos RD presentes | `ls enterprise/l10n_do_edi enterprise/l10n_do_reports` | existen |

### D.2 Contenedor Docker

| Check | Comando | Esperado |
|-------|---------|----------|
| Volumen montado | `docker exec hellenia-dev-odoo-1 test -d /mnt/enterprise/web_enterprise` | exit 0 |
| Custom montado | `docker exec hellenia-dev-odoo-1 test -d /mnt/custom` | exit 0 |
| addons_path | `docker exec hellenia-dev-odoo-1 grep addons_path /etc/odoo/odoo.conf` | incluye `/mnt/enterprise` primero |

### D.3 Base de datos

| Check | SQL / script | Esperado |
|-------|--------------|----------|
| web_enterprise | `SELECT state FROM ir_module_module WHERE name='web_enterprise'` | `installed` |
| Sin licencia aún | `database.enterprise_code` vacío o ausente | OK en E1a |
| Con licencia (E1b) | `database.enterprise_code` con valor | presente |

### D.4 HTTP / UI

| Check | Comando | Esperado |
|-------|---------|----------|
| Login | `curl -sS -o /dev/null -w '%{http_code}' https://dev.hellenia.cloud/web/login` | `200` |
| Versión Odoo | POST `/web/webclient/version_info` | `19.0-20260619` |
| UI Enterprise | Menú Apps muestra módulos Enterprise | visual (post web_enterprise) |

### D.5 Script consolidado

```bash
/opt/odoo-projects/hellenia/scripts/validate-enterprise-dev.sh
```

**Criterio E1a exitoso (sin licencia, sin l10n):**

```
OK  enterprise montado
OK  custom montado
OK  addons_path incluye enterprise
OK  web_enterprise instalado en BD
OK  login HTTP 200
WARN database.enterprise_code vacío  ← esperado si E1b no ejecutado
OK  producción intacta
RESULTADO: OK
```

---

## Parte E — Cómo revertir si falla

### E.1 Fallo antes de instalar `web_enterprise` (solo clone / volúmenes)

```bash
# Eliminar clone Enterprise
rm -rf /opt/odoo-projects/hellenia/enterprise
mkdir -p /opt/odoo-projects/hellenia/enterprise
cp /opt/odoo-projects/hellenia/repository/enterprise/README.md /opt/odoo-projects/hellenia/enterprise/

# Restaurar odoo.conf Community-only (temporal)
# addons_path sin /mnt/enterprise — solo si fallo crítico de arranque

# Recrear contenedor
cd /opt/odoo-projects/hellenia/docker/dev
docker compose --env-file ../../config/dev/.env up -d --force-recreate odoo
```

DEV vuelve a Odoo 19 **Community** funcional.

### E.2 Fallo después de instalar `web_enterprise`

```bash
# 1. Identificar backup pre-E1
ls -lt /opt/odoo-projects/hellenia/backups/dev/

# 2. Detener Odoo
cd /opt/odoo-projects/hellenia/docker/dev
docker compose --env-file ../../config/dev/.env stop odoo

# 3. Restaurar PostgreSQL
source /opt/odoo-projects/hellenia/config/dev/.env
gunzip -c /opt/odoo-projects/hellenia/backups/dev/<TIMESTAMP>/postgres_all.sql.gz \
  | docker exec -i hellenia-dev-db-1 psql -U odoo -d postgres

# 4. Restaurar filestore
docker run --rm \
  -v hellenia-dev_odoo-data:/data \
  -v /opt/odoo-projects/hellenia/backups/dev/<TIMESTAMP>:/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/filestore.tar.gz -C /data"

# 5. Eliminar enterprise clone (opcional)
rm -rf /opt/odoo-projects/hellenia/enterprise/*

# 6. Reiniciar
docker compose --env-file ../../config/dev/.env up -d
```

### E.3 Fallo en registro de licencia (E1b)

- La BD y Enterprise siguen instalados
- Reintentar registro en UI con código correcto
- Si código quedó vinculado a otra BD: contactar soporte Odoo o desvincular en portal
- **No** modificar `database.enterprise_code` manualmente salvo instrucción soporte Odoo

### E.4 Eliminar credenciales GitHub (revocación)

```bash
# En VPS
rm -f /opt/odoo-projects/hellenia/config/credentials/github.env

# En GitHub → Settings → Developer settings → Revoke PAT
```

### E.5 Producción

**Nunca afectada** — rollback E1 solo toca `hellenia-dev-*` y `/opt/odoo-projects/hellenia/enterprise/`.

---

## Parte F — Fases E1 desglosadas (para aprobación granular)

| Sub-fase | Contenido | Requiere aprobación |
|----------|-----------|---------------------|
| **E1a** | PAT vía Cursor SSH → clone → volúmenes → `web_enterprise` → validar | ✅ Esta checklist |
| **E1b** | Registrar `M260616306091776` en UI DEV | Aprobación separada |
| **E1c** | Instalar `l10n_do`, `l10n_do_edi`, `l10n_do_reports` | Aprobación separada |
| **E1d** | Wizard, usuarios, Infile | Fuera de alcance |

**Al aprobar este documento, se entiende aprobación solo de E1a** salvo que se indique lo contrario.

---

## Parte G — Lo que necesito de ti para ejecutar E1a (cuando apruebes)

1. ✅ Confirmación explícita: *"Aprobado E1a"*
2. ✅ GitHub vinculado en portal Odoo (Parte A.1)
3. ✅ PAT creado con permisos de Parte A.2
4. ✅ Enviar en sesión segura:
   - `GITHUB_USER` (username exacto)
   - `GITHUB_TOKEN` (PAT, una sola vez)

Cursor hará el resto por SSH. **No editarás archivos en el VPS.**

---

## Parte H — Referencias

| Documento | Contenido |
|-----------|-----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Capas Community / Enterprise / Custom |
| [E0.6-GITHUB-ENTERPRISE.md](E0.6-GITHUB-ENTERPRISE.md) | Procedimiento GitHub detallado |
| [E0.5-SUBSCRIPTION-VALIDATION.md](E0.5-SUBSCRIPTION-VALIDATION.md) | Política suscripción |
| [E1-ENTERPRISE-STATUS.md](E1-ENTERPRISE-STATUS.md) | Estado actual |
| [GIT-STRATEGY.md](GIT-STRATEGY.md) | Enterprise fuera de Git |
| [ROLLBACK.md](ROLLBACK.md) | Rollback general |

---

## Estado

| Item | Estado |
|------|--------|
| Documento E1-CHECKLIST | ✅ Generado |
| E1a ejecutado | ⛔ Esperando aprobación |
| E1b licencia | ⛔ Bloqueado |
| E1c l10n_do | ⛔ Bloqueado |
| Producción | ⛔ Sin tocar |
