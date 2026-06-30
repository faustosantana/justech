# Estado de Producción — Hellenia

**Última actualización:** 2026-06-30 (Despliegue hellenia-prod)  
**Go-Live / corte DNS:** NO ejecutado

---

## 1. Componentes

| Componente | Estado | Notas |
|------------|--------|-------|
| `odoo-pecv` (Odoo 18 legacy) | 🟢 Operativo | Sin cambios — producción actual |
| `hellenia-dev` | 🟢 Activo | `dev.hellenia.cloud` |
| `hellenia-test` | 🟢 Activo | `test.hellenia.cloud` |
| **`hellenia-prod`** | **🟢 Desplegado** | BD `hellenia_prod`, validación `prod.hellenia.cloud` |
| DNS `odoo.hellenia.cloud` | 🟢 Router Traefik activo | `hellenia-prod` — Fase 13.1 |
| DNS `prod.hellenia.cloud` | ⚪ Sin uso | Reemplazado por `odoo.hellenia.cloud` |
| Licencia EE `hellenia_prod` | 🟢 Registrada | Código `M260616306091776` |

---

## 2. Stack hellenia-prod

| Parámetro | Valor |
|-----------|-------|
| Imagen | `odoo:19.0-20260619` + Enterprise mount |
| BD | `hellenia_prod` (nueva, limpia) |
| `web.base.url` | `https://odoo.hellenia.cloud` |
| `proxy_mode` | `True` |
| `workers` | `2` |
| `dbfilter` | `^hellenia_prod$` |
| Traefik | `Host(\`odoo.hellenia.cloud\`)` — LE válido hasta 2026-09-28 |
| Módulos instalados | ~116 |
| Justech MVP | `justech_l10n_do_base`, `_ncf`, `_reports` ✅ |

---

## 3. Credenciales (DEV = TEST = PROD)

| Usuario | Política |
|---------|----------|
| `admin` | Hash pbkdf2 idéntico en las 3 BD |
| `it@justech.do` | Hash pbkdf2 idéntico en las 3 BD (sync desde DEV) |

Evidencia: `evidence/prod-credentials-sync.json`

---

## 4. Backups y monitoreo

| Ítem | Estado |
|------|--------|
| Backup inicial prod | `backups/hellenia-prod/2026-06-30_1522` |
| Cron backup diario | `02:15` — `backup-hellenia-prod.sh` |
| Cron healthcheck | Lunes `06:30` — `healthcheck.sh` |
| Restore | `scripts/restore-hellenia-prod.sh` |

---

## 5. Validaciones post-despliegue

| Prueba | Resultado |
|--------|-----------|
| Fase 11 (módulos + es_DO) | ✅ PASS |
| Fase 8 (Golden Config) | ✅ PASS |
| Fase 6 MVP Justech | ✅ PASS |
| Fase 12 configuración | ⚠️ PASS con obs (SMTP, bancos, caja — pendiente cliente) |
| Fase 3.5 Golden | ⚠️ Obs (bancos, métodos pago — esperado en BD nueva) |
| HTTPS `odoo.hellenia.cloud` | ✅ HTTP 200 + login Odoo 19 |

---

## 6. Pendiente antes del corte

1. Cliente: catálogos, NCF DGII, SMTP, usuarios `@helleniadr.com`, bancos
2. Smoke test operativo completo en `https://odoo.hellenia.cloud`
3. Aprobación Go-Live
4. Apagar `odoo-pecv` solo con aprobación explícita

---

## 7. Comandos

```bash
./scripts/deploy-hellenia-prod.sh feature/justech-l10n-do-mvp
./scripts/backup-hellenia-prod.sh
./scripts/restore-hellenia-prod.sh /opt/odoo-projects/hellenia/backups/hellenia-prod/<timestamp>
./scripts/healthcheck.sh
```

**Estado:** Producción Odoo 19 **instalada y validada internamente** — lista para validación HTTPS y corte programado.
