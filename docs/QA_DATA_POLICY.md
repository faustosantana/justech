# Política de QA — sin datos ficticios

**Vigente desde:** 2026-06-16  
**Aplica a:** producción (`jaios.justech.do`), staging, scripts, E2E, agentes IA.

---

## Prohibido sin autorización explícita del administrador

- Usuarios (`qa-*@`, `test@`, `demo@`, `example@`, etc.)
- Correos, empresas, clientes, proveedores, contactos
- Cualquier registro de negocio «de prueba» en JAIOS, Odoo, M365, DGCP, CRM, Documentos

---

## Producción

1. **No crear datos** durante QA visual o API en prod.
2. Para probar roles, **solicitar al administrador** qué cuenta real usar.
3. Si no existe cuenta apropiada → **detener la prueba** y pedir autorización.
4. Preferir **entorno QA separado** cuando se requieran datos desechables.

---

## Scripts y automatización

- No incluir seeds que creen usuarios ficticios.
- No hardcodear credenciales QA en repo.
- Tests E2E deben usar **fixtures existentes** o variables de entorno provistas por CI/admin (`JAIOS_TEST_USER_EMAIL`, etc.) — nunca auto-crear usuarios.
- Script permitido para matriz launcher (solo cuentas reales): `backend/scripts/qa_pr12_launcher.py` (admin + usuario estándar).

---

## Datos temporales

Si excepcionalmente el administrador autoriza un dato temporal:

1. Documentar en un issue/ticket: qué, quién, cuándo, propósito.
2. Programar eliminación explícita.
3. Registrar en auditoría (`docs/QA_FICTITIOUS_USERS_REMOVAL.md` o anexo similar).

---

## Referencia histórica

Usuarios QA eliminados en 2026-06-16: ver [`QA_FICTITIOUS_USERS_REMOVAL.md`](QA_FICTITIOUS_USERS_REMOVAL.md).
