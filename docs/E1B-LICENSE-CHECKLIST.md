# E1b — Preparación registro de licencia Enterprise

**Suscripción Hellenia:** `M260616306091776`  
**BD candidata:** `hellenia_dev` (DEV únicamente)  
**Estado:** ⏳ Preparado — **NO registrar hasta aprobación explícita E1b**  
**Fecha:** 2026-06-30

> DEV Enterprise confirmado (`hellenia-odoo:19-enterprise`, `web_enterprise` instalado).  
> Este documento prepara E1b sin ejecutar registro, wizard, usuarios, l10n, ni cambios en TEST/PROD.

---

## 1. Cómo Odoo espera registrar `M260616306091776`

### Procedimiento oficial (Odoo 19 on-premise)

Fuente: [On-premise — Register a database](https://www.odoo.com/documentation/19.0/administration/on_premise.html)

| Paso | Acción oficial |
|------|----------------|
| 1 | Iniciar sesión en Odoo como **administrador** |
| 2 | En el **panel de apps** (dashboard), localizar el **banner** de registro de suscripción |
| 3 | Ingresar el **subscription code**: `M260616306091776` |
| 4 | Enviar / validar — Odoo contacta `services.odoo.com:80` |
| 5 | Si es exitoso: banner **verde** + fecha de expiración visible |
| 6 | La misma fecha aparece al pie de **Ajustes → General** |

### Qué ocurre internamente (sin intervención manual)

| Concepto | Detalle |
|----------|---------|
| Código que ingresa el usuario | **Subscription code** `M260616306091776` |
| Parámetro interno generado | `database.enterprise_code` en `ir_config_parameter` |
| UUID de la BD | `database.uuid` — debe ser **único** en el contrato Odoo |
| Validación recurrente | Semanal hacia `services.odoo.com:80` (Odoo 18+) |
| Contrato en portal | Debe estar **In Progress** en [odoo.com/my/subscriptions](https://www.odoo.com/my/subscriptions) |

### Estado actual DEV (lectura — 2026-06-30)

| Parámetro | Valor actual |
|-----------|--------------|
| `database.enterprise_code` | **Vacío** (no registrado — correcto pre-E1b) |
| `database.uuid` | `0f6fd500-7420-11f1-8965-471541fc31c9` |
| `web_enterprise` | `installed` |
| BD vinculada en portal | Ninguna confirmada |

---

## 2. ¿UI únicamente o también por configuración?

### Método oficial — **UI** (recomendado y documentado)

| Vía | Soportada oficialmente | Notas |
|-----|------------------------|-------|
| Banner en dashboard de apps | ✅ **Sí** | Procedimiento principal documentado |
| Ajustes → General → sección contrato Enterprise | ✅ **Sí** | Alternativa citada en foro/comunidad; misma validación servidor |
| `odoo.conf` / variable de entorno | ❌ **No documentado** | No existe parámetro oficial de subscription code en `odoo.conf` |
| Editar `ir_config_parameter` manualmente | ⚠️ **No oficial** | Workaround de foro; puede fallar validación o dejar BD en estado inconsistente |
| SQL directo en PostgreSQL | ❌ **No** | Fuera de procedimiento; riesgo de licencia inválida |

### Conclusión Hellenia

**Registrar solo vía UI** (banner o Ajustes → General), con administrador existente.  
**No** usar inyección manual de `database.enterprise_code` salvo instrucción explícita de soporte Odoo ante fallo documentado.

### Requisito de red previo al registro

```bash
/opt/odoo-projects/hellenia/scripts/validate-subscription-env.sh
```

| Check | Requisito oficial |
|-------|-------------------|
| DNS `services.odoo.com` | Resuelve |
| HTTP saliente puerto **80** | Abierto de forma **permanente** (incluso post-registro) |

---

## 3. No registrar todavía

| Acción | Estado |
|--------|--------|
| Ingresar `M260616306091776` en UI | ⛔ **Bloqueado** — requiere *"Aprobado E1b"* |
| Modificar `ir_config_parameter` | ⛔ Bloqueado |
| Ejecutar wizard | ⛔ Bloqueado |
| Crear usuarios | ⛔ Bloqueado |
| Instalar l10n_do | ⛔ Bloqueado (E1c) |
| Tocar TEST / PROD | ⛔ Bloqueado |

---

## 4. Checklist de registro (ejecutar solo tras aprobación E1b)

### A. Pre-requisitos portal (usuario — manual)

Verificar en [odoo.com/my/subscriptions](https://www.odoo.com/my/subscriptions):

| # | Verificación | Esperado | ☐ |
|---|--------------|----------|---|
| A.1 | Referencia suscripción | `M260616306091776` | ☐ |
| A.2 | Producto | Odoo Enterprise on-premise | ☐ |
| A.3 | Estado contrato | **In Progress** | ☐ |
| A.4 | BD actualmente vinculada | **Ninguna** | ☐ |
| A.5 | Usuarios internos contratados | Anotar cantidad: ___ | ☐ |
| A.6 | Fecha renovación | Anotar: ___ | ☐ |
| A.7 | UUID en contrato | Sin duplicado con `0f6fd500-7420-11f1-8965-471541fc31c9` | ☐ |

### B. Pre-requisitos técnicos DEV (Cursor — automatizable)

| # | Verificación | Comando / criterio | ☐ |
|---|--------------|-------------------|---|
| B.1 | Backup DEV reciente y válido | `backup-dev.sh` + `verify-backup-dev.sh` | ☐ |
| B.2 | `validate-enterprise-dev.sh` OK | Sin licencia aún (`--no-license` hoy) | ☐ |
| B.3 | Conectividad suscripción | `validate-subscription-env.sh` → OK | ☐ |
| B.4 | `web_enterprise` instalado | `installed` en `ir_module_module` | ☐ |
| B.5 | HTTPS DEV | https://dev.hellenia.cloud → 200 | ☐ |
| B.6 | Acceso admin UI | Credencial admin disponible (sin crear usuarios nuevos) | ☐ |

### C. Registro (usuario + Cursor — solo tras aprobación)

| # | Paso | Responsable | ☐ |
|---|------|-------------|---|
| C.1 | Backup DEV inmediatamente antes | Cursor | ☐ |
| C.2 | Login admin en https://dev.hellenia.cloud | Usuario | ☐ |
| C.3 | Banner apps → ingresar `M260616306091776` | Usuario | ☐ |
| C.4 | Confirmar banner verde + fecha expiración | Usuario | ☐ |
| C.5 | Verificar Ajustes → General (fecha al pie) | Usuario | ☐ |
| C.6 | Cursor: validar `database.enterprise_code` poblado | Cursor | ☐ |
| C.7 | Cursor: `validate-enterprise-dev.sh` (sin `--no-license`) | Cursor | ☐ |
| C.8 | Verificar portal: BD `hellenia_dev` vinculada | Usuario | ☐ |
| C.9 | Documentar fecha expiración y captura (sin commitear secretos) | Usuario/Cursor | ☐ |

### D. Validación post-registro (Cursor)

```bash
# Parámetros internos
docker exec hellenia-dev-db-1 psql -U odoo -d hellenia_dev -tAc \
  "SELECT key, left(value,20) FROM ir_config_parameter WHERE key LIKE 'database.%' ORDER BY 1;"

# Script validación
/opt/odoo-projects/hellenia/scripts/validate-enterprise-dev.sh
```

| Resultado esperado | |
|--------------------|---|
| `database.enterprise_code` | Presente (valor generado por Odoo) |
| Banner / Settings | Fecha expiración coherente con contrato |
| TEST / PROD | Sin cambios |

### E. Si falla el registro (errores oficiales)

| Error documentado | Causa | Acción oficial |
|-------------------|-------|----------------|
| Registration error | Código ya vinculado a otra BD | Desvincular en portal o ticket Odoo |
| Registration error | Contrato no In Progress | Account Manager / portal |
| Registration error | UUID duplicado | Cambiar UUID o ticket soporte |
| Too many users | Usuarios > contratados | Upsell o desactivar usuarios (30 días) |
| Database expired | Renovación vencida | Renovar en portal |

Fuente: [On-premise — Common error messages](https://www.odoo.com/documentation/19.0/administration/on_premise.html)

---

## 5. Riesgos de registrar la licencia en DEV

| Riesgo | Severidad | Detalle |
|--------|-----------|---------|
| **Vinculación exclusiva** | 🔴 Alta | Regla oficial: *"only one database can be linked per subscription"*. Al registrar DEV, `M260616306091776` queda asociado a `hellenia_dev` hasta desvincular o migrar. |
| **Imposibilidad de registrar TEST en paralelo** | 🔴 Alta | `hellenia_test` **no puede** usar el mismo código mientras DEV esté vinculado. TEST debe ser **duplicado neutralizado** de DEV o PROD. |
| **Go-live requiere re-vinculación** | 🟠 Media | Al pasar a PROD futura, el código debe **moverse** de DEV a BD productiva (desvincular DEV → registrar PROD). |
| **Conteo de usuarios** | 🟠 Media | Usuarios internos activos en DEV cuentan contra el contrato. Aviso 30 días si se excede. |
| **Dependencia red permanente** | 🟡 Baja | Puerto 80 saliente a `services.odoo.com` debe permanecer abierto; verificación semanal. |
| **UUID expuesto en contrato** | 🟡 Baja | Tras registro, UUID DEV visible en portal Odoo — esperado. |
| **Operaciones en BD de construcción** | 🟡 Baja | DEV con licencia “viva” puede ejecutar crons/emails reales si no está neutralizada. Mitigación: no crear usuarios operativos; E1c/wizard bloqueados. |
| **Sin impacto en PROD actual** | ✅ Nulo | `odoo-pecv` (Odoo 18) es stack independiente — registro en `hellenia_dev` no lo afecta. |

### Mitigaciones acordadas Hellenia

1. Backup verificado **inmediatamente antes** del registro.
2. Registrar **solo** en `hellenia_dev` durante implementación (decisión documentada en [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md) §7).
3. No crear usuarios internos adicionales hasta conocer cupo contratado.
4. TEST se alimentará por **duplicación + neutralize**, no por segundo registro.

---

## 6. Política TEST y PRODUCCIÓN (post-E1b)

### Regla oficial aplicada

```
Un código M260616306091776  →  una BD vinculada a la vez
Ambientes adicionales       →  duplicar BD + neutralizar
```

### Fases del proyecto Hellenia

| Fase | BD con código activo | DEV (`hellenia_dev`) | TEST (`hellenia_test`) | PROD futura |
|------|----------------------|----------------------|------------------------|-------------|
| **Ahora (implementación)** | `hellenia_dev` tras E1b | Construcción + licencia | Community sin licencia; luego dup. neutralizado de DEV | `odoo-pecv` Odoo 18 — **no tocar** |
| **UAT** | `hellenia_dev` o migrar a TEST* | Desarrollo continuo | Duplicado **neutralizado** de DEV para UAT | Sin cambios |
| **Go-live** | `hellenia_prod` (nueva) | Dup. **neutralizado** de PROD | Dup. **neutralizado** de PROD | **Registrar código aquí** |
| **Operación estable** | PROD | Refresco periódico desde PROD neutralizado | Refresco periódico desde PROD neutralizado | Producción real |

\* Si se necesita TEST Enterprise con datos reales de configuración, duplicar DEV **con neutralize** — no registrar TEST con el mismo código.

### Transición DEV → PROD (cuando llegue go-live)

1. Estabilizar y validar en DEV (licencia + custom + l10n cuando aplique).
2. Duplicar DEV → TEST con `-n` / checkbox neutralize (UAT).
3. Migración / cutover a `hellenia_prod`.
4. **Desvincular** código de `hellenia_dev` en portal (o según procedimiento Odoo).
5. **Registrar** `M260616306091776` en BD productiva.
6. Refrescar DEV y TEST como duplicados neutralizados de PROD.

### TEST y PROD actuales — sin tocar en E1b

| Ambiente | Acción E1b |
|----------|------------|
| TEST (`test.hellenia.cloud`) | **Ninguna** — sigue Community `odoo:19.0-20260619` |
| PROD (`odoo-pecv`, Odoo 18) | **Ninguna** |

---

## 7–10. Restricciones vigentes (E1b preparación)

| # | Restricción | Estado |
|---|-------------|--------|
| 7 | No instalar localización | ⛔ E1c bloqueado |
| 8 | No ejecutar wizard | ⛔ |
| 9 | No crear usuarios | ⛔ |
| 10 | No tocar TEST ni producción | ⛔ |

---

## Secuencia de fases Enterprise (recordatorio)

```
E1a  ✅ DEV Enterprise + web_enterprise (completado)
E1b  ⏳ Registrar M260616306091776 en hellenia_dev (este documento)
E1c  ⛔ l10n_do / l10n_do_edi / l10n_do_reports
E2+  ⛔ Wizard, usuarios operativos, go-live PROD
```

---

## Referencias

| Documento | Contenido |
|-----------|-----------|
| [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md) | Política oficial completa |
| [E0.5-SUBSCRIPTION-VALIDATION.md](E0.5-SUBSCRIPTION-VALIDATION.md) | Validación portal + red |
| [E1-ENTERPRISE-STATUS.md](E1-ENTERPRISE-STATUS.md) | Estado DEV actual |
| [E1-CHECKLIST.md](E1-CHECKLIST.md) | Checklist general E1 |
| [Odoo 19 On-premise](https://www.odoo.com/documentation/19.0/administration/on_premise.html) | Registro oficial |
| [Neutralized database](https://www.odoo.com/documentation/19.0/administration/neutralized_database.html) | Política TEST/DEV |

---

## Aprobación requerida para ejecutar

Cuando estés listo, confirma explícitamente:

> **"Aprobado E1b — registrar licencia en DEV"**

Hasta entonces: **no registrar**, **no reconstruir imagen**, **no tocar TEST/PROD**.
