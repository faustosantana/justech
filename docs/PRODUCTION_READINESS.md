# Preparación para Producción — Hellenia (Fase 12)

**Cliente:** Hellenia, S.R.L.  
**Fecha:** 2026-06-30  
**Fase:** 12 — Preparación final para producción  
**Go-Live:** **NO EJECUTADO**

---

## 1. Resumen ejecutivo

| Clasificación global | **APTO PARA GO-LIVE CON OBSERVACIONES** |
|----------------------|----------------------------------------|
| Listo para ejecutar checklist | **Sí**, tras entregables cliente |
| Producción activada | **No** |
| DNS / licencia prod | **Sin cambios** |

**Separación producto vs cliente:**
- **Justech Dominican Localization** → `custom/justech_l10n_do_*` (producto reutilizable)
- **Hellenia** → parametrización, usuarios, catálogos, rangos DGII, SMTP (específico cliente)

---

## 2. Matriz de certificación por bloque

| Bloque | Descripción | Estado | Notas |
|:------:|-------------|--------|-------|
| 0 | Backups DEV/TEST/odoo-pecv | **PASS** | `2026-06-30_1458`–`1459` |
| 1 | Limpieza datos prueba | **PASS CON OBS** | TEST: BD staging con histórico UAT; **prod = BD nueva** |
| 2 | Validar configuración | **PASS CON OBS** | Empresa/RNC/idioma OK; SMTP prod pendiente |
| 3 | Usuarios reales | **PASS CON OBS** | Plantillas listas; **pendiente lista Hellenia** |
| 4 | Catálogos importación | **PASS CON OBS** | Plantillas CSV; **archivos no entregados** |
| 5 | NCF DGII oficiales | **FAIL** | **Pendiente autorización DGII del cliente** |
| 6 | SMTP corporativo | **FAIL** | **Pendiente credenciales Hellenia** |
| 7 | Validación flujo completo datos reales | **FAIL** | Bloqueado por catálogo + NCF reales |
| 8 | Stack producción (sin activar) | **PASS CON OBS** | Plantilla `hellenia-prod` lista |
| 9 | Go-Live check integral | **PASS CON OBS** | Ver [GO_LIVE_CHECKLIST.md](GO_LIVE_CHECKLIST.md) |

---

## 3. Qué falta para poner Hellenia en producción

| # | Pendiente | Tipo |
|---|-----------|------|
| 1 | Aprobación escrita Go-Live | Cliente + Justech |
| 2 | Archivos catálogo (clientes, proveedores, productos, existencias) | **Cliente** |
| 3 | Rangos NCF autorizados DGII | **Cliente / Contador** |
| 4 | Credenciales SMTP corporativo | **Cliente** |
| 5 | Lista usuarios `@helleniadr.com` con roles | **Cliente** |
| 6 | Desplegar `hellenia-prod` + Traefik (sin DNS hasta validación) | **Justech** |
| 7 | Registrar licencia EE en `hellenia_prod` | **Justech** |
| 8 | Importaciones y validación flujo completo | **Justech** (post entrega datos) |
| 9 | Backup final `odoo-pecv` + corte DNS | **Justech** (ventana Go-Live) |

---

## 4. Acciones por responsable

### Cliente (Hellenia)

1. Entregar CSV catálogos según plantillas `data/hellenia/templates/`
2. Entregar autorizaciones NCF DGII (B01, B02, B03, B04, B11, B13)
3. Proporcionar credenciales SMTP (servidor, puerto, usuario, contraseña, from)
4. Confirmar lista usuarios y roles ([USER_SETUP.md](USER_SETUP.md))
5. Aprobar ventana de mantenimiento y Go-Live

### Justech

1. Crear BD `hellenia_prod` limpia (no clonar histórico UAT)
2. Aplicar parametrización Fase 8 + español Fase 11
3. Importar datos tras entrega cliente
4. Configurar NCF, usuarios, SMTP
5. Ejecutar [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)
6. Activar Traefik/DNS tras validación interna

---

## 5. ¿Está Hellenia lista para ejecutar el Go-Live?

**Preparación técnica:** **Sí** — documentación, scripts, plantillas y stack definidos.

**Ejecución del corte:** **No aún** — bloqueado por entregables cliente (NCF, SMTP, catálogos, usuarios).

```
VEREDICTO: APTO PARA GO-LIVE CON OBSERVACIONES
           Esperar entregables cliente + aprobación explícita
           Go-Live NO ejecutado
```

---

## 6. Evidencia

| Archivo | Contenido |
|---------|-----------|
| `evidence/phase12-backups-manifest.json` | Rutas backups |
| `evidence/phase12-cleanup-test.json` | Limpieza TEST |
| `evidence/phase12-cleanup-dev.json` | Limpieza DEV |
| `evidence/phase12-config-test.json` | Config TEST |
| `evidence/phase12-config-dev.json` | Config DEV |

```bash
./scripts/run-phase12-hellenia-prep.sh
```

---

**Detenido.** Esperando aprobación explícita y entregables del cliente.
