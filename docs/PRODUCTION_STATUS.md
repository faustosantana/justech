# Estado de Producción — Hellenia

**Última actualización:** 2026-06-30 (Fase 12)  
**Go-Live:** NO ejecutado

---

## 1. Componentes

| Componente | Estado | Notas |
|------------|--------|-------|
| `odoo-pecv` (Odoo 18 legacy) | 🟢 Operativo | Sin cambios Fase 12 |
| `hellenia-dev` | 🟢 Activo | Limpieza piloto parcial |
| `hellenia-test` | 🟢 Activo | Staging; histórico UAT en backup |
| `hellenia-prod` | ⚪ No desplegado | Plantilla en `docker/production/` |
| DNS `odoo.hellenia.cloud` | ⚪ Sin router Traefik | Sin cambio |
| Licencia EE prod | ⚪ No registrada | Política 1 BD/código |

---

## 2. Backups Fase 12

| Ambiente | Timestamp | Ruta |
|----------|-----------|------|
| DEV | `2026-06-30_1458` | `/opt/odoo-projects/hellenia/backups/dev/2026-06-30_1458` |
| TEST | `2026-06-30_1459` | `/opt/odoo-projects/hellenia/backups/test/2026-06-30_1459` |
| odoo-pecv | `2026-06-30_1459` | `/opt/odoo-projects/hellenia/backups/production/2026-06-30_1459` |

Manifest: `evidence/phase12-backups-manifest.json`

---

## 3. Limpieza datos prueba

### TEST (`phase12-cleanup-test.json`)

| Métrica | Valor |
|---------|-------|
| Reportes fiscales eliminados | 6 |
| Partners UAT eliminados | parcial |
| Rangos UAT con facturas publicadas | conservados en backup |
| **Estrategia prod** | BD `hellenia_prod` **nueva y vacía** |

### DEV (`phase12-cleanup-dev.json`)

| Métrica | Valor |
|---------|-------|
| `clean_state` | ✅ (sin partners UAT; PHASE4 lab residual documentado) |
| UAT-PILOT eliminados | ✅ |

---

## 4. Stack producción (preparado, no activo)

| Artefacto | Ubicación |
|-----------|-----------|
| docker-compose | `docker/production/docker-compose.yml` |
| odoo.conf ejemplo | `config/production/odoo.conf.example` |
| .env ejemplo | `config/production/.env.example` |
| Backup script | `scripts/backup-hellenia-prod.sh` |
| Guía despliegue | `PRODUCTION_DEPLOYMENT_GUIDE.md` |

---

## 5. Separación Justech / Hellenia

| Justech (producto) | Hellenia (cliente) |
|--------------------|-------------------|
| `justech_l10n_do_base` | Empresa, RNC, dirección |
| `justech_l10n_do_ncf` | Rangos DGII autorizados |
| `justech_l10n_do_reports` | Catálogo, precios, existencias |
| Tests unitarios producto | Usuarios `@helleniadr.com` |
| Roadmap v1.1+ | SMTP, bancos operativos |

Módulos `hellenia_*` en repo: **esqueletos — no instalar**.

---

## 6. Scripts Fase 12

```bash
./scripts/run-phase12-hellenia-prep.sh      # Orquestador completo
./scripts/phase12-cleanup-hellenia.py       # vía run-odoo-shell-env.sh
./scripts/phase12-validate-configuration.py
./scripts/backup-hellenia-prod.sh           # post Go-Live
```

---

## 7. Próximo hito

1. Cliente entrega catálogos + NCF + SMTP + usuarios  
2. Aprobación Go-Live  
3. Justech ejecuta `PRODUCTION_CHECKLIST.md`  
4. Corte `odoo-pecv` → `hellenia_prod`

**Estado:** DETENIDO — esperando aprobación y entregables.
