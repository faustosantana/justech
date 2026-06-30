# Enterprise sin registro de licencia — Alcance y limitaciones

**Proyecto:** Hellenia / Justech  
**Suscripción (no registrada aún):** `M260616306091776`  
**BD laboratorio:** `hellenia_dev` — imagen `hellenia-odoo:19-enterprise`, `web_enterprise` instalado  
**Estrategia vigente (2026-06-30):** DEV como laboratorio funcional **sin** registrar el código hasta go-live en BD definitiva  
**Estado:** Documento de análisis — **no ejecutar E1b**

---

## Resumen ejecutivo

| Pregunta | Respuesta corta |
|----------|-----------------|
| ¿Podemos seguir implementando en DEV sin registrar? | **Sí**, durante el período de trial Enterprise documentado por Odoo |
| ¿Qué bloquea el registro? | Nada técnico inmediato; el bloqueo aparece tras **expiración** de trial / BD no registrada |
| ¿Registrar en go-live? | **Sí** — política acordada: código en BD productiva definitiva |
| ¿Afecta TEST/PROD actuales? | **No** — stacks independientes |

---

## Contexto técnico DEV (verificado 2026-06-30)

| Elemento | Estado |
|----------|--------|
| Imagen | `hellenia-odoo:19-enterprise` |
| `web_enterprise` | `installed` |
| `database.enterprise_code` | **Vacío** (sin registro) |
| `database.expiration_date` | **Aún no establecido** en `ir_config_parameter` |
| `database.uuid` | `0f6fd500-7420-11f1-8965-471541fc31c9` |
| `database.create_date` | `2026-06-30 01:07:27` |
| Usuarios activos | 1 (admin) |
| Módulos RD en imagen | `l10n_do` (Community), `l10n_do_reports`, `l10n_do_check_printing` (Enterprise) |
| `l10n_do_edi` | **Ausente** en tarball `odoo_19.0+e.20260629` y en imagen DEV |

---

## Base oficial vs interpretación

### Lo que documenta Odoo 19 on-premise

Fuente: [On-premise](https://www.odoo.com/documentation/19.0/administration/on_premise.html)

| Hecho oficial | Implicación |
|---------------|-------------|
| Registro = ingresar subscription code en banner UI | Genera `database.enterprise_code` y fecha de expiración contractual |
| Sin registro exitoso | Banner de registro / trial visible en dashboard |
| BD con módulos Enterprise instalados | Considerada instancia Enterprise (comportamiento reforzado desde v17 según foro Odoo) |
| Verificación semanal | `services.odoo.com:80` — requiere salida HTTP permanente |
| *Database expired* | Mensaje **bloqueante** tras countdown (documentación histórica: aviso ~30 días antes del bloqueo en escenarios de usuarios/expiración) |
| Una BD por código | Al registrar en go-live, solo la BD definitiva debe quedar vinculada |

### Lo que Odoo **no** documenta con precisión

| Tema | Estado |
|------|--------|
| Duración exacta del trial sin código en on-premise 19.0 | **No especificado** en docs públicas — observar `database.expiration_date` cuando aparezca |
| Lista de módulos EE bloqueados uno a uno sin registro | **No hay lista oficial** — la restricción global es por **estado de BD** (trial / expirada), no por módulo individual |
| Si `l10n_do_edi` existe en Enterprise 19.0 on-premise | **No en tarball Hellenia** — ver §5 |

> **Regla Hellenia:** Distinguimos hechos oficiales, observación en DEV, y recomendación de proyecto.

---

## 1. Qué módulos Enterprise funcionan sin registrar

### Principio técnico

Con `web_enterprise` instalado y código Enterprise en imagen:

- Los módulos Enterprise son **código Python/XML en disco** — Odoo puede **instalarlos** (`-i` / Apps) sin que `database.enterprise_code` esté poblado.
- El control de licencia opera a nivel de **base de datos** (trial, expiración, validación periódica con Odoo), no como comprobación individual por cada módulo al instalar.

### Categorías

| Categoría | Sin registro (fase trial) | Tras expiración BD |
|-----------|---------------------------|---------------------|
| **UI Enterprise** (`web_enterprise`, `web_mobile`, tema EE) | ✅ Funciona | ⛔ Riesgo bloqueo global BD |
| **Módulos EE instalables** (contabilidad avanzada, inventario barcode, MRP, etc.) | ✅ Instalables y usables en laboratorio | ⛔ Mismo riesgo |
| **Módulos Community** | ✅ Siempre (salvo BD expirada por EE) | ⛔ Si BD bloqueada |
| **Módulos custom** (`custom/`) | ✅ Desarrollo completo | ⛔ Si BD bloqueada |
| **Servicios Odoo IAP** (SMS, OCR, etc.) | ⚠️ Requieren créditos/cuenta Odoo aparte | ⚠️ |
| **Soporte Odoo Enterprise** | ❌ BD no vinculada al contrato | ❌ |

### Módulos Enterprise ya operativos en DEV

| Módulo | Estado |
|--------|--------|
| `web_enterprise` | installed |
| `web_mobile` | installed (auto_install con web_enterprise) |

### Módulos Enterprise RD disponibles en imagen actual

| Módulo | En imagen | Instalable sin registro* |
|--------|-----------|--------------------------|
| `l10n_do_reports` | ✅ | ✅ (técnico) |
| `l10n_do_check_printing` | ✅ | ✅ (técnico) |
| `l10n_do_edi` | ❌ **No existe en 19.0+e.20260629** | ❌ N/A |

\*Durante período trial / antes de expiración documentada.

---

## 2. Limitaciones que aparecerán

### Inmediatas (ya o pronto)

| Limitación | Severidad | Detalle |
|------------|-----------|---------|
| **Banner de registro** | 🟡 | Dashboard pide subscription code — esperado |
| **Modo trial Enterprise** | 🟡 | BD tratada como EE en evaluación (foro Odoo v17+) |
| **Sin vinculación contractual** | 🟡 | Portal Odoo no muestra `hellenia_dev` como BD licenciada |
| **Sin soporte oficial sobre esta BD** | 🟡 | Hasta registrar en BD definitiva |

### Cuando Odoo establezca expiración (`database.expiration_date`)

| Limitación | Severidad | Detalle |
|------------|-----------|---------|
| **Countdown en UI** | 🟠 | Aviso de días restantes |
| **Presión temporal** | 🟠 | Planificar go-live o registro temporal si trial corto |
| **BD expirada** | 🔴 | Documentación oficial: mensaje **bloqueante** — operación restringida |

### Operativas (laboratorio)

| Limitación | Mitigación DEV |
|------------|----------------|
| Emails reales a clientes | Desactivar outgoing mail / usar mail catcher |
| Pagos / bancos en vivo | No configurar proveedores producción |
| eNCF / DGII real | No aplica sin `l10n_do_edi`; usar datos demo |
| Infile producción | Solo en go-live — ver [INFILE-REQUIREMENTS.md](INFILE-REQUIREMENTS.md) |

### Lo que **no** limita el registro diferido

| Acción | ¿Bloqueada por falta de registro? |
|--------|-----------------------------------|
| Instalar módulos (CLI / Apps) | **No** (técnicamente) |
| Configurar empresa / plan contable | **No** |
| Desarrollar módulos custom | **No** |
| Ejecutar wizard de configuración | **No** |
| Crear usuarios de prueba | **No** (pero cuentan si luego se registra) |

---

## 3. ¿Podemos instalar `l10n_do`?

| Campo | Valor |
|-------|-------|
| **Origen** | Community (`/usr/lib/.../odoo/addons/l10n_do`) |
| **Requiere registro EE** | **No** — módulo Community |
| **Recomendación Hellenia** | ✅ **Sí, instalar en DEV** para laboratorio RD |
| **Prerrequisitos** | País empresa = DO; backup DEV previo |

Documentación RD: localización base (plan contable, impuestos ITBIS, NCF tradicionales).

---

## 4. ¿Podemos instalar `l10n_do_edi`?

| Campo | Valor |
|-------|-------|
| **En tarball / imagen DEV** | ❌ **No presente** en `odoo_19.0+e.20260629` |
| **Instalable sin registro** | ❌ **No aplica** — módulo no disponible en esta versión desplegada |
| **Acción requerida** | Evaluar tarball Enterprise más reciente (ej. 19.3+ cuando exista tag estable) o confirmar con Odoo disponibilidad eNCF on-premise 19.0 |

**Conclusión:** No es limitación de licencia — es **ausencia de módulo** en el paquete actual.

---

## 5. ¿Podemos instalar `l10n_do_reports`?

| Campo | Valor |
|-------|-------|
| **Origen** | Enterprise (`/opt/odoo/enterprise/addons/l10n_do_reports`) |
| **Requiere registro previo** | **No documentado** como prerrequisito de instalación |
| **Dependencias típicas** | `l10n_do` instalado |
| **Recomendación Hellenia** | ✅ **Sí en DEV laboratorio** (tras `l10n_do`) |
| **Riesgo** | Solo expiración global de BD trial |

---

## 6. ¿Podemos configurar la empresa?

| Acción | Sin registro |
|--------|--------------|
| Razón social, RNC, dirección DO | ✅ |
| Logo, moneda DOP | ✅ |
| País / fiscal país = República Dominicana | ✅ |
| Diarios contables, impuestos (con `l10n_do`) | ✅ |
| Usuarios y permisos de prueba | ✅ |
| Ajustes → General (pie sin fecha contractual) | ✅ — sin fecha de contrato hasta E1b/go-live |

**Recomendación:** Configurar empresa completa en DEV — es el objetivo del laboratorio.

---

## 7. ¿Podemos ejecutar el wizard?

| Campo | Valor |
|-------|-------|
| **Técnicamente** | ✅ Sí — onboarding / configuración inicial no requiere `database.enterprise_code` |
| **Política anterior** | Wizard bloqueado en E0–E1a |
| **Política nueva (laboratorio)** | ✅ **Permitido en DEV** para avanzar implementación funcional |
| **Restricción** | No ejecutar wizard en TEST/PROD |

El wizard facilita: país, industria, chart of accounts, apps iniciales.

---

## 8. ¿Podemos desarrollar módulos custom?

| Campo | Valor |
|-------|-------|
| **Respuesta** | ✅ **Sí — alcance completo** |
| **Ubicación** | `custom/` — horneado en imagen o volumen según pipeline |
| **Patrón** | `_inherit` sobre `l10n_do*` / módulos estándar — nunca parchear `enterprise/` |
| **Licencia registro** | **No afecta** compilación ni carga de módulos LGPL custom |
| **Módulos previstos** | `hellenia_base`, `hellenia_account`, `hellenia_inventory`, etc. |

---

## 9. ¿Podemos probar flujos completos?

### Matriz de flujos

| Flujo | Sin registro (DEV lab) | Notas |
|-------|------------------------|-------|
| Ventas → factura → pago (sin eNCF) | ✅ | Con `l10n_do` |
| Compras / inventario / POS | ✅ | Instalar apps necesarias |
| Contabilidad / reportes estándar | ✅ | `account_accountant` si se requiere suite EE |
| Reportes fiscales RD (`l10n_do_reports`) | ✅ | Tras instalar módulo |
| **eNCF / factura electrónica DGII** | ❌ | Sin `l10n_do_edi` en paquete 19.0 actual |
| **Infile / envío fiscal real** | ❌ | Go-live + módulo + credenciales |
| Emails transaccionales | ⚠️ | Usar ambiente prueba / desactivar |
| Portal cliente / eCommerce | ✅ | Cuidado SEO / datos reales |
| Integraciones bancarias | ⚠️ | No usar cuentas producción |
| Multi-usuario / permisos | ✅ | |
| Flujo DEV → TEST (futuro) | ⏳ | Duplicar + neutralize — TEST sin tocar ahora |

### Período trial

Durante trial Enterprise, los flujos **no registrados** son funcionales para laboratorio. Monitorear:

```bash
docker exec hellenia-dev-db-1 psql -U odoo -d hellenia_dev -tAc \
  "SELECT key, value FROM ir_config_parameter WHERE key IN ('database.expiration_date','database.enterprise_code');"
```

---

## Política de licenciamiento revisada

### Antes (E1b inmediato)

```
E1a → E1b registrar DEV → E1c l10n → implementación
```

### Ahora (laboratorio sin registro)

```
E1a ✅ → implementación funcional en DEV (sin E1b)
         → go-live: registrar M260616306091776 en BD PROD definitiva
         → DEV/TEST post-go-live: duplicados neutralizados de PROD
```

| Ambiente | Registro `M260616306091776` |
|----------|----------------------------|
| **DEV** (`hellenia_dev`) | ⛔ **No** hasta decisión explícita o nunca (si go-live directo en PROD nueva) |
| **TEST** | ⛔ No — duplicado neutralizado cuando aplique |
| **PROD futura** | ✅ **Sí** — único registro en go-live |
| **PROD actual** (`odoo-pecv` Odoo 18) | ⛔ Sin cambios |

### Ventajas de diferir registro

| Ventaja | Detalle |
|---------|---------|
| Código preservado para PROD | Una sola vinculación en BD definitiva |
| DEV como sandbox | Iteración sin consumir slot contractual |
| Alineado con doc Odoo | Test/dev = duplicar BD, no segundo registro |

### Riesgos de diferir registro

| Riesgo | Mitigación |
|--------|------------|
| Expiración trial DEV | Monitorear `database.expiration_date`; registrar solo si necesario extender, o rebuild DEV |
| Banner permanente | Aceptable en laboratorio |
| Sin soporte Odoo sobre DEV | Documentación interna + foro/ticket solo para PROD |

---

## Orden de trabajo recomendado (sin E1b)

```
1. Backup DEV verificado (backup-dev.sh + verify-backup-dev.sh)
2. Instalar l10n_do (+ account_accountant si aplica)
3. Instalar l10n_do_reports
4. Configurar empresa RD (RNC, impuestos, diarios)
5. Ejecutar wizard / configuración funcional
6. Desarrollar e instalar módulos custom
7. Probar flujos operativos (sin eNCF real)
8. Documentar gaps (l10n_do_edi ausente en 19.0)
── go-live ──
9.  Migrar / crear BD PROD → registrar M260616306091776
10. E1c eNCF cuando módulo + Infile disponibles
```

---

## Restricciones que siguen vigentes

| Regla | Estado |
|-------|--------|
| NO registrar `M260616306091776` en DEV | ✅ Hasta nueva aprobación o go-live |
| NO tocar TEST | ✅ |
| NO tocar PRODUCCIÓN (`odoo-pecv`) | ✅ |
| NO reconstruir imagen DEV sin causa | ✅ |
| eNCF / Infile producción | ⛔ Hasta go-live |

---

## Monitoreo recomendado

| Frecuencia | Check |
|------------|-------|
| Semanal | `database.expiration_date` en DEV |
| Pre-cambio mayor | `backup-dev.sh` + `verify-backup-dev.sh` |
| Pre-instalar módulo EE | Confirmar módulo existe en imagen: `docker exec hellenia-dev-odoo-1 ls /opt/odoo/enterprise/addons/<mod>` |
| Pre-go-live | [E1B-LICENSE-CHECKLIST.md](E1B-LICENSE-CHECKLIST.md) |

---

## Referencias

| Documento | Contenido |
|-----------|-----------|
| [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md) | Política oficial una BD por código |
| [E1B-LICENSE-CHECKLIST.md](E1B-LICENSE-CHECKLIST.md) | Registro diferido — ejecutar en go-live |
| [E1-ENTERPRISE-STATUS.md](E1-ENTERPRISE-STATUS.md) | Estado técnico DEV |
| [L10N-RD-READINESS.md](L10N-RD-READINESS.md) | Stack RD (actualizar prerrequisito E1b) |
| [Odoo 19 On-premise](https://www.odoo.com/documentation/19.0/administration/on_premise.html) | Trial / expiración / registro |

---

**Última actualización:** 2026-06-30  
**Próxima revisión:** Cuando aparezca `database.expiration_date` en DEV o al planificar go-live.
