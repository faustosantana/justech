# Fase 7 — Preparación del entorno UAT

**Cliente:** Hellenia, S.R.L.  
**Fecha:** 2026-06-30  
**Fase:** 7 — Preparación operativa (sin Go-Live)  
**Estado:** **PREPARADO CON PENDIENTES** — esperando contraseña `it@justech.do` y aprobación para UAT funcional

---

## 1. Resumen ejecutivo

| Área | Estado |
|------|--------|
| DEV (`dev.hellenia.cloud`) | ✅ Operativo — MVP + Sprint 0 validado |
| TEST (`test.hellenia.cloud`) | ✅ Operativo — clon neutralizado DEV, UAT técnico listo |
| PRODUCCIÓN (`odoo.hellenia.cloud`) | ⚠️ DNS listo — router Traefik **pendiente** (sin mover `odoo-pecv`) |
| Usuario `it@justech.do` | ⏳ **Pendiente** — requiere contraseña indicada por Hellenia |
| Usuario `admin` | ✅ Preservado como recuperación de emergencia |
| Configuración empresa | ✅ Correcta en DEV y TEST |
| Seguridad MVP (ACL + rules) | ✅ Verificada |
| Carga datos reales / Go-Live | ❌ No iniciado (por diseño) |

---

## 2. Usuario administrador técnico

### 2.1 Especificación

| Campo | Valor |
|-------|-------|
| Nombre | Justech IT |
| Login | `it@justech.do` |
| Correo | `it@justech.do` |
| Idioma | Español (República Dominicana) — `es_DO` disponible |
| Zona horaria | `America/Santo_Domingo` |
| Grupos | Settings, Administration, Accounting/Sales/Purchase/Inventory Administrator, Technical Features |
| POS Administrator | No aplica — `point_of_sale` **no instalado** |

### 2.2 Estado de creación

**No creado** — la contraseña debe ser indicada explícitamente por Hellenia. No se inventó ninguna contraseña (instrucción de proyecto).

Cuando se reciba la contraseña:

```bash
export JUSTECH_IT_PASSWORD='<contraseña indicada por Hellenia>'
./scripts/create-justech-it-user.sh dev
./scripts/create-justech-it-user.sh test
```

Script: `scripts/create-justech-it-user.py` / `create-justech-it-user.sh`

### 2.3 Usuario `admin`

| Ambiente | Login | Activo | Rol |
|----------|-------|--------|-----|
| DEV | `admin` | Sí | Recuperación de emergencia |
| TEST | `admin` | Sí | Recuperación de emergencia |

**No eliminado** en ningún ambiente.

---

## 3. Auditoría de usuarios

Inventario completo: [USER_ACCESS_MATRIX.md](USER_ACCESS_MATRIX.md)  
Evidencia JSON: `evidence/uat-user-audit-dev.json`, `evidence/uat-user-audit-test.json`

### Hallazgos

| Verificación | DEV | TEST |
|--------------|-----|------|
| Usuarios operativos activos | 1 (`admin`) | 1 (`admin`) |
| Usuarios de prueba accidentales | ❌ Ninguno | ❌ Ninguno |
| Logins `*test*`, `*fiscal*` | ❌ Ninguno | ❌ Ninguno |
| Correos `@test.com` / `@hellenia.test` | ❌ Ninguno | ❌ Ninguno |
| BD neutralizada | No | Sí (`database.is_neutralized=true`) |

---

## 4. Validación de ambientes

| URL | DNS | HTTPS | Certificado | HTTP `/web/login` | Docker |
|-----|-----|-------|-------------|-------------------|--------|
| https://dev.hellenia.cloud | `2.25.69.179` | ✅ | Let's Encrypt | 200 | `hellenia-dev-odoo-1` healthy |
| https://test.hellenia.cloud | `2.25.69.179` | ✅ | Let's Encrypt | 200 | `hellenia-test-odoo-1` healthy |
| https://odoo.hellenia.cloud | `2.25.69.179` | ⚠️ | Traefik default (no LE) | 404 | Sin router — ver [PRODUCTION_URL_READINESS.md](PRODUCTION_URL_READINESS.md) |

### Corrección aplicada en TEST

- `web.base.url` actualizado de `https://dev.hellenia.cloud` → `https://test.hellenia.cloud`
- Contenedor TEST reiniciado (estaba detenido post-validación Sprint 0)

### Producción actual (solo lectura)

- Stack operativo: `odoo-pecv` (Odoo **18**) en `odoo-pecv.srv1784296.hstgr.cloud`
- **No modificado** en esta fase

---

## 5. Configuración general empresa

Verificado en DEV y TEST (`scripts/audit-company-config.py`):

| Campo | Esperado | DEV | TEST |
|-------|----------|-----|------|
| Empresa | Hellenia, S.R.L. | ✅ | ✅ |
| RNC | 133621282 | ✅ | ✅ |
| Moneda | DOP | ✅ | ✅ |
| País | DO | ✅ | ✅ |
| Fiscal Justech | habilitado | ✅ | ✅ |
| Timezone usuarios | America/Santo_Domingo | ✅ | ✅ |

---

## 6. Seguridad

| Control | Estado |
|---------|--------|
| `admin` activo (emergencia) | ✅ DEV + TEST |
| `it@justech.do` administrador | ⏳ Pendiente creación |
| ACL Justech (`ir.model.access`) | ✅ Instaladas |
| Record rules multiempresa Justech | ✅ 6 reglas activas |
| Sin usuarios duplicados | ✅ |
| Sin correos de prueba operativos | ✅ |
| `proxy_mode` | ✅ `True` en DEV y TEST |

---

## 7. Acciones realizadas

1. Reinicio stack TEST Odoo para UAT.
2. Corrección `web.base.url` en TEST.
3. Auditoría usuarios DEV y TEST.
4. Auditoría configuración empresa.
5. Verificación HTTPS / Traefik / DNS tres dominios.
6. Scripts Fase 7 en `scripts/` (auditoría + creación usuario).
7. Documentación Fase 7 generada.

## Acciones NO realizadas (por reglas de fase)

- ❌ Go-Live / migración producción
- ❌ Carga datos reales
- ❌ Inicio POS
- ❌ Modificación MVP
- ❌ Nuevas funcionalidades
- ❌ Creación `it@justech.do` sin contraseña autorizada

---

## 8. Certificación Fase 7

```
FASE 7 — PREPARACIÓN UAT
DEV:                    OPERATIVO
TEST:                   OPERATIVO (neutralizado)
PRODUCCIÓN (odoo.*):    DNS OK — router Traefik PENDIENTE
it@justech.do:          PENDIENTE (contraseña)
admin:                  PRESERVADO
Empresa/RNC/moneda:     OK
Seguridad MVP:          OK
UAT funcional:          NO INICIADO — esperar aprobación
Go-Live:                NO INICIADO
Fecha:                  2026-06-30
```

---

## 9. Próximo paso

1. Hellenia proporciona contraseña para `it@justech.do`.
2. Ejecutar `create-justech-it-user.sh` en DEV y TEST.
3. Aprobación explícita para **iniciar UAT funcional** con usuarios de negocio.
4. Go-Live: completar checklist producción (`PRODUCTION_INFRASTRUCTURE_CHECKLIST.md`).
