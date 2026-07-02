# Credenciales VPS — Hellenia Odoo

**Directorio:** `/opt/odoo-projects/hellenia/config/credentials/`  
**Permisos:** `chmod 700` directorio; `chmod 600` archivos sensibles  
**Git:** Excluido en `.gitignore` — nunca commitear

---

## Método preferido: SSH Key para `odoo/enterprise`

| Archivo | Propósito | Permisos |
|---------|-----------|----------|
| `github_ed25519` | Clave privada SSH dedicada | 600 |
| `github_ed25519.pub` | Clave pública (agregar en GitHub) | 644 |
| `ssh_config` | Config SSH para usar clave dedicada con github.com | 600 |

### Pasos (usuario + Cursor)

1. **Usuario:** Vincular cuenta GitHub en portal Odoo (GitHub Users)
2. **Cursor (E1):** Generar par de claves en este directorio
3. **Usuario:** Copiar contenido de `github_ed25519.pub` → GitHub → Settings → SSH and GPG keys → New SSH key
4. **Cursor (E1):** Verificar con `git ls-remote git@github.com:odoo/enterprise.git`

Ver procedimiento completo: [docs/E0.6-GITHUB-ENTERPRISE.md](../../docs/E0.6-GITHUB-ENTERPRISE.md)

---

## Fallback: PAT (solo si SSH no aplica)

| Archivo | Propósito |
|---------|-----------|
| `github.env` | `GITHUB_USER` + `GITHUB_TOKEN` — **evitar** si SSH funciona |

Ver plantilla: `github.env.example`

---

## Rotación y revocación

| Método | Revocación |
|--------|------------|
| SSH Key | Eliminar key en GitHub → Settings → SSH keys |
| PAT | Revocar en GitHub → Developer settings → Tokens |

```bash
# Eliminar credenciales en VPS
rm -f /opt/odoo-projects/hellenia/config/credentials/github_ed25519*
rm -f /opt/odoo-projects/hellenia/config/credentials/ssh_config
rm -f /opt/odoo-projects/hellenia/config/credentials/github.env
```
