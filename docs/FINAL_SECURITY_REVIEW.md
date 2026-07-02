# Revisión de Seguridad Final — Fase 11

**Cliente:** Hellenia, S.R.L.  
**Fecha:** 2026-06-30  
**Referencias:** Fase 7.5, Sprint 0, UAT Fase 9  
**Evidencia:** `evidence/security-audit-dev.json`, `evidence/security-audit-test.json`

---

## 1. Resumen y calificación

| Dimensión | DEV | TEST | Calificación |
|-----------|-----|------|:------------:|
| Usuarios y grupos | ✅ | ✅ | **A-** |
| ACL custom | ✅ | ✅ | **A** |
| Record rules | ✅ | ✅ | **A** |
| Contraseñas / secrets | ✅ | ✅ | **B+** |
| SMTP | ❌ | ❌ | **D** |
| Infra SSH / firewall | ⚠️ | ⚠️ | **B** |
| Docker / Linux perms | ✅ | ✅ | **B+** |
| PostgreSQL acceso | ✅ | ✅ | **A-** |
| Hardening aplicación | ✅ | ✅ | **A-** |

**Calificación seguridad global: B+ (84/100)**

---

## 2. Usuarios

| Usuario | Ambiente | Rol | Go-Live |
|---------|----------|-----|---------|
| `admin` | DEV, TEST | Emergencia | Deshabilitar post-Go-Live recomendado |
| `it@justech.do` | DEV, TEST | TI + Fiscal Manager | Mantener técnico |
| Usuarios Hellenia | — | No creados | **P0 pre-Go-Live** |

**Regla Fase 11 respetada:** No se crearon usuarios funcionales adicionales.

---

## 3. Grupos y ACL

### 3.1 Grupos Justech

| Grupo | XML ID | Usuarios |
|-------|--------|----------|
| Dominican Fiscal User | `group_justech_do_fiscal_user` | 0 |
| Dominican Fiscal Manager | `group_justech_do_fiscal_manager` | 1 |

### 3.2 ACL (10 entradas)

| Modelo | Read | Write | Create | Unlink |
|--------|:----:|:-----:|:------:|:------:|
| `justech.do.fiscal.document.type` | User+ | Manager | Manager | Manager |
| `justech.do.ncf.range` | User+ | Manager | Manager | Manager |
| `justech.do.ncf.consumption` | User+ | Manager | — | — |
| `justech.do.fiscal.report` | User+ | User+ | User+ | Manager |

**Evaluación:** Principio mínimo privilegio aplicado. Consumo NCF sin unlink — correcto.

### 3.3 Record rules (6 reglas Justech)

Dominio estándar `company_id in company_ids` — cerrado Sprint 0 TD-001.

---

## 4. Controles servidor (post Sprint 0)

| Control | Implementación | Estado |
|---------|----------------|--------|
| `action_void_ncf` grupo servidor | `AccessError` si no Fiscal Manager | ✅ |
| Motivo void obligatorio | Validación Python | ✅ |
| NCF único SQL | Índice parcial posted | ✅ |
| Concurrencia NCF | Advisory lock | ✅ |
| Sin `sudo()` en custom | Auditoría código | ✅ |

---

## 5. Credenciales y secrets

| Item | Estado |
|------|--------|
| Contraseñas en repo | ❌ Ninguna |
| `.env` en git | ❌ Solo `.example` |
| `admin_passwd` plantilla | Placeholder `CHANGE_ME` |
| Claves SSH VPS | Fuera repo |
| Código licencia EE | Documentado, no en repo |

---

## 6. Infraestructura

| Control | Estado Fase 10 | Observación |
|---------|----------------|-------------|
| SSL DEV/TEST | ✅ Let's Encrypt | |
| SSL `odoo.hellenia.cloud` | ❌ Sin router | P0 Go-Live |
| Fail2ban | ⚠️ No verificado activo | P2 |
| Firewall UFW | ⚠️ Documentado | Validar pre-Go-Live |
| Backups cifrados | ⚠️ At-rest VPS | P2 |
| TEST neutralizado | ✅ | Sin correo real |

---

## 7. PostgreSQL

| Aspecto | Estado |
|---------|--------|
| Usuario por stack | ✅ Aislado |
| Puerto expuesto internet | ❌ Solo red Docker |
| Superuser app | No — rol dedicado |

---

## 8. Rotación y hardening pendiente

| Item | Prioridad | Acción |
|------|-----------|--------|
| Rotar `admin_passwd` prod | P0 | Al desplegar |
| SMTP credenciales | P0 | Configurar |
| Deshabilitar `admin` prod | P1 | Post Go-Live |
| 2FA usuarios admin | P2 | Roadmap |
| Rotación backup offsite | P2 | Post Go-Live |

---

## 9. Matriz riesgos seguridad

| ID | Riesgo | Impacto | Prioridad |
|----|--------|---------|-----------|
| SEC-01 | Sin SMTP — reset password manual | Medio | P0 |
| SEC-02 | `admin` activo en prod futuro | Alto | P1 |
| SEC-03 | Sin monitoreo alertas | Medio | P1 |
| SEC-04 | Sin swap — DoS memoria | Medio | P1 |

---

## 10. Certificación bloque 4 (seguridad)

| Clasificación | **PASS CON OBSERVACIONES** |
|---------------|---------------------------|
| Bloqueante seguridad Go-Live | SMTP + usuarios prod (operativo, no código) |
| Código aplicación | **Apto** |

---

**Producción NO modificada. Sin nuevos usuarios creados.**
