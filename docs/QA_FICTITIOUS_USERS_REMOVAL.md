# Auditoría — eliminación usuarios QA ficticios

**Fecha eliminación:** 2026-06-16  
**Autorizado por:** administrador (Fausto)  
**Entorno:** JAIOS prod, tenant `justech`

---

## Usuarios eliminados

| Correo | Creado (UTC) | Propósito original | Odoo | M365 |
|--------|--------------|-------------------|------|------|
| qa-ventas@justech.do | 2026-06-15 21:41 | PR-1.2 launcher rol ventas | No | No |
| qa-licitaciones@justech.do | 2026-06-15 21:41 | PR-1.2 launcher rol licitaciones | No | No |
| qa-gerencia@justech.do | 2026-06-15 22:08 | PR-1.5 QA visual prod | No | No |

---

## Acciones ejecutadas

1. `DELETE` 23 `refresh_tokens` asociados.
2. `DELETE` 3 `tenant_memberships`.
3. `DELETE` 3 filas `users`.
4. Verificación post-eliminación: **0** usuarios `qa-*@justech.do` en BD.

---

## Artefactos repo eliminados

| Archivo | Motivo |
|---------|--------|
| `backend/scripts/seed_qa_roles.py` | Seed auto-creación QA |
| `backend/scripts/qa_pr12_visual_postdeploy.py` | Creaba/actualizaba QA + credenciales |
| `backend/scripts/qa_pr12_ui_playwright.py` | Credenciales QA hardcodeadas |
| `backend/scripts/qa_pr15_visual_prod.py` | Creaba qa-gerencia + credenciales |
| `e2e/qa-pr12-ui.spec.ts` | E2E con usuarios QA |
| `e2e/qa-pr12-ui.mjs` | Idem |

---

## Documentación histórica conservada

Los informes PR-1.2 / PR-1.5 **mencionan** estos usuarios como evidencia de pruebas ya ejecutadas. No implican que deban existir de nuevo.

Política vigente: [`QA_DATA_POLICY.md`](QA_DATA_POLICY.md)

---

## Validación final

```bash
# Usuarios QA en BD (debe retornar 0 filas)
docker compose exec -T postgres psql -U jaios -d jaios -c \
  "SELECT email FROM users WHERE email ILIKE 'qa-%@justech.do';"

# Referencias auto-seed en repo (debe retornar vacío)
rg 'seed_qa_roles|qa-ventas@|qa-licitaciones@|qa-gerencia@|JaiosQA' --glob '!docs/**'
```
