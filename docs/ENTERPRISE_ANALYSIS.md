# Análisis Odoo Enterprise — Hellenia

**Fecha:** 2026-06-30  
**Suscripción:** `M260616306091776` (activa, sin BD vinculada)  
**Decisión estratégica:** Implementación definitiva en **Odoo Enterprise** (no Community)  
**Estado:** Análisis — **sin ejecución** de wizard, usuarios, módulos ni localización

---

## Resumen ejecutivo

| Tema | Conclusión |
|------|------------|
| Procedimiento Docker oficial | Imagen Community + addons Enterprise montados; **no existe imagen Enterprise en Docker Hub** |
| Conversión Community → Enterprise | Instalar `web_enterprise`, actualizar `addons_path`, registrar suscripción |
| Código de suscripción | `M260616306091776` — ingresar en UI tras tener Enterprise operativo |
| Repositorio Enterprise | `github.com/odoo/enterprise` (rama `19.0`) o descarga en `odoo.com/page/download` |
| Localización RD completa | Requiere Enterprise (`l10n_do_edi`, `l10n_do_reports`) + servicio externo **Infile** |
| Próximo paso | Aprobar este análisis → ejecutar plan DEV (documento al final) |

**Referencias oficiales:**
- [Switch Community to Enterprise](https://www.odoo.com/documentation/19.0/administration/on_premise/community_to_enterprise.html)
- [On-premise — Register database](https://www.odoo.com/documentation/19.0/administration/on_premise.html)
- [Docker Hub odoo — Enterprise note](https://hub.docker.com/_/odoo)
- [Localización RD](https://www.odoo.com/documentation/19.0/applications/finance/fiscal_localizations/dominican_republic.html)

---

## 1. Procedimiento oficial: Docker Community → Enterprise

Odoo **no publica** una imagen Docker Enterprise en Docker Hub. La documentación oficial del contenedor indica explícitamente:

> *"Although there is no official Odoo Enterprise Docker image, the Enterprise modules can be mounted using the above mentioned method."*

### Procedimiento recomendado por Odoo (sin atajos)

Este es el flujo alineado con la documentación oficial de instalación on-premise y conversión a Enterprise:

#### Paso 1 — Obtener código Enterprise (ver sección 4)

Descargar o clonar el repositorio `odoo/enterprise` en la rama **`19.0`** (misma versión mayor que la imagen Docker).

#### Paso 2 — Montar addons Enterprise en Docker

Mantener la imagen Community oficial (`odoo:19.0-20260619`) y montar Enterprise como volumen:

```yaml
services:
  odoo:
    image: odoo:19.0-20260619
    volumes:
      - odoo-data:/var/lib/odoo
      - /opt/odoo-projects/hellenia/enterprise:/mnt/enterprise:ro
      - ${ADDONS_PATH}:/mnt/extra-addons:ro
      - ${ODOO_CONF_PATH}:/etc/odoo/odoo.conf:ro
```

#### Paso 3 — Configurar `addons_path` (orden crítico)

En `odoo.conf`, **Enterprise debe ir primero** para que los módulos Enterprise sobrescriban equivalentes Community:

```ini
[options]
addons_path = /mnt/enterprise,/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
```

> La documentación de conversión a Enterprise indica actualizar `--addons-path` antes de instalar `web_enterprise`.

#### Paso 4 — Backup de la base de datos

Antes de cualquier cambio:

```bash
/opt/odoo-projects/hellenia/scripts/backup-dev.sh
```

#### Paso 5 — Instalar módulo `web_enterprise`

Con el contenedor apuntando al path Enterprise:

```bash
docker exec hellenia-dev-odoo-1 odoo \
  -d hellenia_dev --db_host=db --db_user=odoo --db_password="$DB_PASSWORD" \
  -i web_enterprise --stop-after-init
```

Este es el paso **oficial** documentado en [Switch from Community to Enterprise](https://www.odoo.com/documentation/19.0/administration/on_premise/community_to_enterprise.html).

#### Paso 6 — Reiniciar Odoo y verificar UI Enterprise

Tras reiniciar, la interfaz debe mostrar el cliente web Enterprise (menús y apps Enterprise disponibles).

#### Paso 7 — Registrar suscripción (ver sección 2)

Ingresar `M260616306091776` en el banner o en Ajustes.

### Lo que NO es procedimiento oficial

| Enfoque | Por qué evitarlo |
|---------|------------------|
| Imagen `latest` o tags flotantes | Política del proyecto; impredecible en producción |
| Copiar módulos Enterprise a Git público | Viola licencia OPL-1.0 |
| Omitir `web_enterprise` | La BD no activa capacidades Enterprise |
| `addons_path` con Enterprise al final | Módulos Community prevalecen; Enterprise no aplica |
| Registrar suscripción antes de tener Enterprise instalado | El código valida contra módulos Enterprise presentes |

### Alternativa oficial: imagen custom (build)

Odoo documenta también construir una imagen Docker propia:

```dockerfile
FROM odoo:19.0-20260619
USER root
COPY ./enterprise /mnt/enterprise
RUN chown -R odoo:odoo /mnt/enterprise
USER odoo
```

La imagen resultante debe almacenarse en un **registro privado** (no Docker Hub público). Para Hellenia, el enfoque de **volumen montado** es más simple y equivalente funcionalmente.

---

## 2. Registro de la suscripción `M260616306091776`

### Procedimiento oficial

Según [On-premise — Register a database](https://www.odoo.com/documentation/19.0/administration/on_premise.html):

1. Iniciar sesión en Odoo como **administrador**
2. En el panel de apps, usar el **banner** de registro de suscripción
3. Ingresar el código: **`M260616306091776`**
4. Si es exitoso, el banner se vuelve **verde** y muestra la fecha de expiración
5. La fecha también aparece al pie de **Ajustes → General**

### Requisitos de red

El servidor Odoo debe poder abrir conexiones salientes hacia:

| Versión Odoo | Host | Puerto |
|--------------|------|--------|
| 18.0 y superior | `services.odoo.com` | **80** (HTTP) |

Este puerto debe permanecer abierto **incluso después** del registro (verificación semanal).

### Reglas de licenciamiento críticas

| Regla | Implicación para Hellenia |
|-------|---------------------------|
| **1 código = 1 base de datos** | `M260616306091776` solo puede vincularse a **una** BD activa |
| BD de prueba | Duplicar BD de producción (con neutralización) para dev/test adicionales |
| Usuarios internos | No exceder usuarios contratados; si no, aviso 30 días antes de expiración |
| Estado suscripción | Debe mostrar **"In Progress"** en [odoo.com/my/subscriptions](https://www.odoo.com/my/subscriptions) |

### Estrategia recomendada para ambientes

Dado que el código solo vincula **una** BD:

| Ambiente | Estrategia suscripción |
|----------|------------------------|
| **DEV** (primera activación) | Registrar `M260616306091776` aquí durante fase de implementación |
| **TEST** | Duplicar BD DEV neutralizada, **o** segunda suscripción si Odoo lo provisiona |
| **PROD** | Tras go-live, **re-vincular** el mismo código a PROD (desvincular DEV) |

> Confirmar con Account Manager de Odoo si el contrato incluye múltiples ambientes o si TEST debe usar BD duplicada neutralizada.

---

## 3. Requisitos exactos: códigos, contrato, repositorio, licencia

| Concepto | Qué es | Quién lo provee | Cuándo se usa |
|----------|--------|-----------------|---------------|
| **Subscription code** | Código `M260616306091776` ingresado en UI | Odoo (email / portal) | Al registrar BD en banner o Ajustes |
| **enterprise_code** | Parámetro interno `database.enterprise_code` en `ir.config_parameter` | **Generado automáticamente** por Odoo al registrar | No se ingresa manualmente en flujo normal |
| **Contrato Enterprise** | Acuerdo de suscripción en [odoo.com/my/subscriptions](https://www.odoo.com/my/subscriptions) | Odoo S.A. | Valida usuarios, vigencia, soporte |
| **Repositorio Enterprise** | `https://github.com/odoo/enterprise.git` rama `19.0` | Odoo (acceso privado GitHub) | Despliegue on-premise |
| **Descarga alternativa** | Tarball Enterprise en [odoo.com/page/download](https://www.odoo.com/page/download) | Odoo (con código suscripción) | Si no se usa GitHub |
| **Licencia código** | **OPL-1.0** (Enterprise) + **LGPL-3.0** (Community) | Odoo S.A. | Válida solo con suscripción activa |

### Aclaraciones importantes

**`subscription_code` vs `enterprise_code`:**
- El usuario ingresa **`M260616306091776`** (subscription code)
- Odoo valida contra `services.odoo.com` y almacena internamente `database.enterprise_code`
- Modificar `database.enterprise_code` manualmente en parámetros del sistema **no es el procedimiento oficial** (solo workaround de foro ante fallos)

**`web_enterprise`:**
- Módulo puente obligatorio; activa UI y funcionalidades Enterprise
- Debe instalarse **después** de configurar `addons_path` con Enterprise

**Usuarios licenciados:**
- Cada usuario interno activo cuenta para la suscripción
- Usuarios portal/website generalmente no cuentan igual; verificar contrato

---

## 4. Obtención oficial de módulos Enterprise

### Método A — GitHub (recomendado para actualizaciones)

**Procedimiento oficial:**

1. Crear cuenta GitHub (si no existe)
2. Ir a [odoo.com/my/subscriptions](https://www.odoo.com/my/subscriptions)
3. Seleccionar suscripción `M260616306091776`
4. En sección **GitHub Users**, agregar el username de GitHub
5. Esperar invitación/acceso al repo privado (minutos)
6. Verificar acceso: `https://github.com/odoo/enterprise` (no debe dar 404)
7. Clonar en el VPS:

```bash
cd /opt/odoo-projects/hellenia
git clone https://github.com/odoo/enterprise.git --branch 19.0 --depth 1 enterprise
```

> Usar **Personal Access Token (PAT)** de GitHub para autenticación en servidor sin interacción. No commitear el repo Enterprise a Git público.

### Método B — Descarga directa (sin GitHub)

1. Ir a [odoo.com/page/download](https://www.odoo.com/page/download)
2. Ingresar código `M260616306091776`
3. Descargar paquete Enterprise para versión 19
4. Extraer en `/opt/odoo-projects/hellenia/enterprise/`

### Método C — Actualizaciones periódicas

```bash
cd /opt/odoo-projects/hellenia/enterprise
git fetch origin 19.0
git checkout 19.0
git pull origin 19.0
```

Reiniciar Odoo tras actualizar código Enterprise. Aplicar `-u` solo a módulos afectados si hay release notes.

### Lo que NO existe oficialmente

- Imagen `odoo:enterprise` en Docker Hub público
- Repo Enterprise abierto sin suscripción activa
- Instalación Enterprise sin módulo `web_enterprise`

---

## 5. Contexto Hellenia

**Empresa:** Hellenia, S.R.L. — mobiliario y decoración (retail/distribución)  
**País:** República Dominicana (RNC, ITBIS, eNCF DGII)  
**Infraestructura actual:**

| Ambiente | Odoo | Edición | URL |
|----------|------|---------|-----|
| DEV | 19.0-20260619 | Community | dev.hellenia.cloud |
| TEST | 19.0-20260619 | Community | test.hellenia.cloud |
| PROD | 18.x | Community | odoo-pecv (sin migrar) |

**Objetivo definitivo:** Odoo Enterprise 19 + localización RD oficial + eNCF + DGII, sin módulos de terceros salvo aprobación.

---

## 6. Análisis de módulos Enterprise solicitados

Escala de recomendación para Hellenia:

- 🔴 **Esencial** — requerido para objetivos del proyecto
- 🟠 **Alto valor** — aporta beneficio claro al negocio
- 🟡 **Evaluar** — útil según proceso; no urgente
- ⚪ **Bajo / diferir** — poco relevante para retail mobiliario

### Tabla resumen

| Módulo | Técnico | Recomendación | Licencia | Dependencias clave |
|--------|---------|---------------|----------|-------------------|
| **Accounting Enterprise** | `account_accountant` + suite | 🔴 Esencial | Enterprise | `account`, `web_enterprise` |
| **Documents** | `documents` | 🟠 Alto valor | Enterprise | `web_enterprise`, `mail` |
| **Sign** | `sign` | 🟠 Alto valor | Enterprise | `documents` (recomendado), `mail` |
| **Knowledge** | `knowledge` | 🟡 Evaluar | Enterprise | `web_enterprise` |
| **Spreadsheet** | `spreadsheet_edition` | 🟡 Evaluar | Enterprise | `web_enterprise` |
| **Approvals** | `approvals` | 🟠 Alto valor | Enterprise | `mail` |
| **Barcode** | `stock_barcode` | 🟠 Alto valor | Enterprise | `stock`, `web_enterprise` |
| **Studio** | `web_studio` | 🟡 Evaluar | Enterprise | `web_enterprise` |
| **Project** | `project` | 🟡 Evaluar | Community base; EE mejora reporting | `web_enterprise` |
| **Timesheets** | `timesheet_grid` | ⚪ Diferir | Enterprise | `hr_timesheet`, `web_enterprise` |
| **Planning** | `planning` | ⚪ Diferir | Enterprise | `hr`, `web_enterprise` |
| **Expenses** | `hr_expense` + EE extras | 🟠 Alto valor | Enterprise | `hr`, `account` |
| **Helpdesk** | `helpdesk` | 🟡 Evaluar | Enterprise | `mail`, `web_enterprise` |
| **VoIP** | `voip` | ⚪ Diferir | Enterprise | Proveedor VoIP externo |
| **Quality** | `quality` | ⚪ Diferir | Enterprise | `stock`; orientado a manufactura |
| **Maintenance** | `maintenance` | ⚪ Diferir | Community existe; EE añade planning | `mail` |
| **Rental** | `sale_renting` | ⚪ Diferir | Enterprise | Solo si alquilan mobiliario |

---

### 6.1 Documents (`documents`)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Repositorio central de facturas, contratos, fichas técnicas, OCR en facturas proveedor, workflows de aprobación documental |
| **Valor Hellenia** | Digitalizar documentación de proveedores, fichas de producto, contratos con clientes corporativos |
| **Dependencias** | `web_enterprise`, `mail`; integra con Contabilidad, Compras, Ventas |
| **Requisitos** | Solo licencia Enterprise |
| **Impacto** | Medio-alto; reduce papel y mejora trazabilidad |
| **Licenciamiento** | Incluido en suscripción Enterprise |

### 6.2 Sign (`sign`)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Firma electrónica de contratos, cotizaciones, documentos HR |
| **Valor Hellenia** | Contratos de venta, entregas, acuerdos con proveedores |
| **Dependencias** | `mail`; sinergia con `documents` |
| **Requisitos** | Licencia Enterprise; SMS/créditos adicionales si se usa autenticación SMS |
| **Impacto** | Medio; acelera cierre comercial |
| **Licenciamiento** | Incluido; algunos métodos de autenticación pueden requerir créditos IAP |

### 6.3 Knowledge (`knowledge`)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Wiki interna, procedimientos, base de conocimiento |
| **Valor Hellenia** | Manuales de atención al cliente, guías de producto, procesos internos |
| **Dependencias** | `web_enterprise` |
| **Requisitos** | Solo licencia |
| **Impacto** | Bajo-medio en fase inicial |
| **Licenciamiento** | Incluido |

### 6.4 Spreadsheet (`spreadsheet_edition`)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Hojas de cálculo conectadas a datos Odoo en tiempo real |
| **Valor Hellenia** | Análisis de ventas por línea de producto, margen, inventario |
| **Dependencias** | `web_enterprise`; datos de módulos instalados |
| **Requisitos** | Solo licencia |
| **Impacto** | Medio para finanzas/comercial |
| **Licenciamiento** | Incluido |

### 6.5 Approvals (`approvals`)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Flujos de aprobación para compras, gastos, ausencias |
| **Valor Hellenia** | Control de órdenes de compra, gastos de empleados |
| **Dependencias** | `mail`; integra con Compras, HR, Gastos |
| **Requisitos** | Solo licencia |
| **Impacto** | Alto para gobernanza |
| **Licenciamiento** | Incluido |

### 6.6 Accounting Enterprise (`account_accountant` y relacionados)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Conciliación bancaria avanzada, reportes financieros dinámicos, activos, diferidos, OCR facturas, auditoría, lock dates |
| **Valor Hellenia** | 🔴 **Crítico** — base contable profesional + prerequisito para reportes RD |
| **Dependencias** | `account`, `web_enterprise` |
| **Requisitos** | Licencia Enterprise |
| **Impacto** | **Muy alto** — núcleo del ERP financiero |
| **Licenciamiento** | Incluido; usuarios contables cuentan en suscripción |

**Módulos contables Enterprise típicamente incluidos:**
- `account_accountant` — modo contable completo
- `account_reports` — reportes financieros
- `account_asset` — activos fijos
- `account_auto_transfer` — transferencias automáticas
- Conciliación bancaria avanzada, follow-up cobros

### 6.7 Barcode (`stock_barcode`)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Operaciones de almacén con escáner (recepciones, entregas, inventario) |
| **Valor Hellenia** | Alto si manejan almacén con movimientos frecuentes |
| **Dependencias** | `stock`, `web_enterprise`, `barcodes` |
| **Requisitos** | Licencia; hardware escáner o app móvil |
| **Impacto** | Alto en logística |
| **Licenciamiento** | Incluido |

### 6.8 Rental (`sale_renting`)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Alquiler de productos con contratos y facturación recurrente |
| **Valor Hellenia** | ⚪ Bajo — Hellenia vende mobiliario, no indica modelo de alquiler |
| **Dependencias** | `sale`, `stock` |
| **Requisitos** | Licencia |
| **Impacto** | Nulo salvo que ofrezcan rental |
| **Licenciamiento** | Incluido |

### 6.9 Studio (`web_studio`)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Personalización sin código: campos, vistas, automatizaciones |
| **Valor Hellenia** | Adaptar flujos sin desarrollo custom (alineado con política sin terceros) |
| **Dependencias** | `web_enterprise` |
| **Requisitos** | Licencia; usar con disciplina para no sobre-complicar |
| **Impacto** | Medio-alto a largo plazo |
| **Licenciamiento** | Incluido |

### 6.10 VoIP (`voip`)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Llamadas desde CRM/Odoo, click-to-dial |
| **Dependencias** | Proveedor VoIP (OnSIP, etc.) |
| **Valor Hellenia** | ⚪ Bajo en fase inicial |
| **Requisitos** | Licencia + **servicio VoIP externo** |
| **Impacto** | Bajo |
| **Licenciamiento** | Módulo incluido; telefonía es costo aparte |

### 6.11 Helpdesk (`helpdesk`)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Tickets de soporte post-venta, SLA, portal cliente |
| **Valor Hellenia** | Medio — útil para garantías y servicio post-venta |
| **Dependencias** | `mail`, `portal`, `web_enterprise` |
| **Requisitos** | Licencia |
| **Impacto** | Medio |
| **Licenciamiento** | Incluido |

### 6.12 Quality (`quality`)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Control de calidad en manufactura |
| **Valor Hellenia** | ⚪ Muy bajo — no es manufactura |
| **Dependencias** | `stock`; orientado a MRP |
| **Impacto** | Nulo |
| **Licenciamiento** | Incluido |

### 6.13 Maintenance (`maintenance`)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Mantenimiento de equipos/maquinaria |
| **Valor Hellenia** | ⚪ Bajo — retail mobiliario |
| **Impacto** | Bajo |
| **Licenciamiento** | Community base; EE añade integraciones |

### 6.14 Project (`project`)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Gestión de proyectos, tareas, entregas |
| **Valor Hellenia** | 🟡 Si hacen instalaciones/entregas complejas a clientes |
| **Dependencias** | `mail`; EE añade `timesheet_grid` linkage |
| **Impacto** | Medio si hay proyectos de instalación |
| **Licenciamiento** | Base en Community; funciones avanzadas en EE |

### 6.15 Planning (`planning`)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Planificación de turnos y recursos |
| **Valor Hellenia** | ⚪ Bajo salvo equipos de campo |
| **Impacto** | Bajo |
| **Licenciamiento** | Enterprise |

### 6.16 Timesheets (`timesheet_grid`)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Hojas de tiempo con vista grid |
| **Valor Hellenia** | ⚪ Bajo en fase inicial |
| **Dependencias** | `hr_timesheet`, `web_enterprise` |
| **Impacto** | Bajo |
| **Licenciamiento** | Enterprise |

### 6.17 Expenses (`hr_expense` + Enterprise)

| Aspecto | Detalle |
|---------|---------|
| **Ventajas** | Gastos de empleados, OCR recibos, flujos de aprobación |
| **Valor Hellenia** | 🟠 Alto — gastos de viaje, compras menores |
| **Dependencias** | `hr`, `account` |
| **Impacto** | Medio-alto |
| **Licenciamiento** | Incluido |

---

## 7. Localización República Dominicana — Informe Enterprise

### Módulos oficiales RD

| Módulo | Repositorio | Edición | Incluido en licencia | Configuración requerida | Servicio externo |
|--------|-------------|---------|----------------------|-------------------------|------------------|
| **`l10n_do`** | `odoo/odoo` (Community) | Community + Enterprise | ✅ LGPL | País DO, RNC, moneda DOP | Ninguno |
| **`l10n_do_edi`** | `odoo/enterprise` | **Solo Enterprise** | ✅ OPL con suscripción | Diarios ventas, tipos documento, rangos eNCF | **Infile** (obligatorio prod) |
| **`l10n_do_reports`** | `odoo/enterprise` | **Solo Enterprise** | ✅ OPL | Instalar tras `l10n_do` | Ninguno |
| **`l10n_do_check_printing`** | `odoo/enterprise` | **Solo Enterprise** | ✅ OPL | Formatos banco | Ninguno |

### NCF (Comprobantes Fiscales)

| Aspecto | Detalle |
|---------|--------|
| **Incluido** | Secuencias y tipos NCF en `l10n_do` (B01, B02, B14, etc.) |
| **Configuración** | Rangos autorizados DGII, diarios con "Use Documents", tipos por partner |
| **Licencia** | `l10n_do` no requiere Enterprise; operación fiscal completa en papel limitada sin EDI |
| **Externo** | Autorización de rangos ante **DGII** |

### eNCF (Comprobantes Fiscales Electrónicos)

| Aspecto | Detalle |
|---------|--------|
| **Incluido** | `l10n_do_edi` — E31, E32, E33, E34 |
| **Configuración** | Credenciales Infile, ambiente Demo/Test/Prod, rangos eNCF DGII |
| **Licencia** | **Requiere Enterprise activo** + suscripción registrada |
| **Externo** | **Infile** — contrato como Facturador Electrónico; credenciales Username, Password, Security Key, Llave |

### DGII

| Funcionalidad | Módulo | Enterprise | Externo |
|---------------|--------|------------|---------|
| Plan contable DGII/NIIF | `l10n_do` | No requerido | — |
| ITBIS, retenciones, propina | `l10n_do` | No requerido | — |
| Envío XML ECF | `l10n_do_edi` | **Sí** | Infile → DGII |
| Estado documento DGII | `l10n_do_edi` | **Sí** | Infile |
| Reportes fiscales RD | `l10n_do_reports` | **Sí** | — |
| Cheques formato RD | `l10n_do_check_printing` | **Sí** | Banco |

### Infile — Servicio externo obligatorio para eNCF

| Ambiente | Infile requerido | Genera documentos legales |
|----------|------------------|---------------------------|
| **Demo** | No | No — pruebas locales |
| **Test** | Sí (credenciales) | Sí — ambiente certificación |
| **Production** | Sí (contrato activo) | Sí — documentos legales DGII |

**Procedimiento Infile (resumen):**
1. Contrato directo con Infile como Facturador Electrónico
2. Obtener credenciales API
3. Solicitar rangos eNCF a DGII
4. Configurar en Odoo: Contabilidad → Configuración → Facturación electrónica RD

### Soporte oficial Enterprise para RD

- Documentación: [Dominican Republic — Odoo 19](https://www.odoo.com/documentation/19.0/applications/finance/fiscal_localizations/dominican_republic.html)
- `l10n_do_edi` integra con Infile como proveedor certificado oficial en la documentación Odoo
- Soporte Odoo Enterprise incluye localizaciones oficiales (según contrato Success Pack)
- **No se requieren módulos de terceros** (p. ej. ncf_manager de OCA/iterativo) si se usa stack oficial Enterprise

### Nota de versión

La localización RD con eNCF fue anunciada en foros Odoo para **19.3+** en SaaS. Para on-premise Enterprise **19.0**, verificar presencia de `l10n_do_edi` en rama `19.0` del repo Enterprise tras clonar. Si no está disponible en `19.0`, evaluar upgrade a **19.3** cuando esté estable en Docker Hub con tag fijo.

---

## 8. Propuesta de módulos — Fase 1 Hellenia (para aprobación)

### Instalar en Fase 1 (post-conversión Enterprise)

| Prioridad | Módulos | Justificación |
|-----------|---------|---------------|
| 🔴 P0 | `web_enterprise` | Activación Enterprise |
| 🔴 P0 | `account_accountant` + suite contable EE | Contabilidad profesional |
| 🔴 P0 | `l10n_do` | Localización RD base |
| 🔴 P0 | `l10n_do_edi` | eNCF / DGII |
| 🔴 P0 | `l10n_do_reports` | Reportes fiscales RD |
| 🟠 P1 | `stock`, `purchase`, `sale` | Operación comercial (Community base) |
| 🟠 P1 | `stock_barcode` | Almacén |
| 🟠 P1 | `documents` | Gestión documental |
| 🟠 P1 | `approvals` | Control compras/gastos |
| 🟠 P1 | `hr_expense` | Gastos empleados |

### Fase 2 (tras estabilización)

| Módulos | Justificación |
|---------|---------------|
| `sign` | Contratos digitales |
| `spreadsheet_edition` | Análisis financiero |
| `helpdesk` | Post-venta |
| `l10n_do_check_printing` | Si pagan con cheques |
| `web_studio` | Ajustes sin desarrollo |

### No instalar (fase actual)

`rental`, `quality`, `voip`, `planning`, `timesheet_grid`, `maintenance` (salvo cambio de alcance)

---

## 9. Licenciamiento — Resumen

| Elemento | Detalle |
|----------|---------|
| **Contrato** | Suscripción Enterprise `M260616306091776` |
| **Modelo** | Por usuario interno / año (verificar cantidad contratada en portal) |
| **Código** | 1 BD activa por código |
| **Código fuente Enterprise** | Uso permitido con suscripción activa; no redistribuir |
| **Soporte Odoo** | Incluido según plan (verificar Success Pack) |
| **Infile** | Contrato y costo **separado** de Odoo |
| **DGII** | Rangos NCF/eNCF — trámite gubernamental, sin costo Odoo |

---

## 10. Impacto en infraestructura Hellenia

| Componente | Cambio requerido |
|------------|------------------|
| Imagen Docker | **Sin cambio** — seguir `odoo:19.0-20260619` |
| Volumen nuevo | `/opt/odoo-projects/hellenia/enterprise/` (repo clonado) |
| `odoo.conf` | Actualizar `addons_path` (Enterprise primero) |
| `docker-compose.yml` | Montar volumen `/mnt/enterprise` |
| PostgreSQL | Sin cambio |
| Traefik | Sin cambio |
| Red saliente | Abrir `services.odoo.com:80` |
| Git | **NO** commitear carpeta `enterprise/` |
| `.gitignore` | Agregar `enterprise/` |
| Producción | **No tocar** hasta aprobación |

---

## 11. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| 1 código = 1 BD | Registrar en DEV; TEST por duplicado neutralizado |
| Enterprise en Git público | `.gitignore`, solo en VPS |
| `l10n_do_edi` no en rama 19.0 | Verificar tras clone; plan B: Odoo 19.3 pin |
| Infile no contratado | Usar ambiente Demo para desarrollo; contratar antes de UAT fiscal |
| Usuarios excedidos | Contar solo internos activos; desactivar usuarios prueba |
| Upgrade BD Community→Enterprise | BD actual solo tiene `base`; bajo riesgo |

---

## 12. Plan de instalación Enterprise en DEV (propuesta — NO ejecutar)

> **Estado:** Pendiente de aprobación de este documento.

### Fase E0 — Preparación (sin tocar Odoo)

- [ ] Verificar suscripción `M260616306091776` en estado **In Progress** en portal Odoo
- [ ] Vincular usuario GitHub en [odoo.com/my/subscriptions](https://www.odoo.com/my/subscriptions)
- [ ] Confirmar cantidad de usuarios licenciados
- [ ] Verificar conectividad saliente VPS → `services.odoo.com:80`
- [ ] Backup DEV: `backup-dev.sh`

### Fase E1 — Código Enterprise en VPS

```bash
cd /opt/odoo-projects/hellenia
git clone https://github.com/odoo/enterprise.git --branch 19.0 --depth 1 enterprise
ls enterprise/l10n_do_edi  # verificar módulos RD
chmod -R a+rX enterprise/
```

### Fase E2 — Configuración Docker DEV

- Actualizar `config/dev/odoo.conf`:

```ini
addons_path = /mnt/enterprise,/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
```

- Actualizar `docker/dev/docker-compose.yml`:

```yaml
volumes:
  - /opt/odoo-projects/hellenia/enterprise:/mnt/enterprise:ro
```

- Recrear contenedor: `docker compose up -d odoo`

### Fase E3 — Activar Enterprise en BD

```bash
source config/dev/.env
docker exec hellenia-dev-odoo-1 odoo \
  -d hellenia_dev --db_host=db --db_user=odoo --db_password="$DB_PASSWORD" \
  -i web_enterprise --stop-after-init
docker compose restart odoo
```

### Fase E4 — Registrar suscripción

1. Abrir https://dev.hellenia.cloud
2. Ingresar código **`M260616306091776`**
3. Verificar banner verde + fecha expiración

### Fase E5 — Validación (sin instalar módulos de negocio)

- [ ] UI muestra edición Enterprise
- [ ] Apps Enterprise visibles en buscador
- [ ] `validate-odoo19.sh dev` — ajustar para verificar Enterprise
- [ ] Producción intacta

### Fase E6 — Instalación módulos (solo tras segunda aprobación)

Instalar en orden P0 → P1 según tabla sección 8. **No ejecutar en esta fase.**

### Fase E7 — TEST

Replicar configuración exacta en TEST **después** de DEV estable. Para suscripción: duplicar BD DEV neutralizada o gestionar con Odoo según contrato.

---

## 13. Checklist de aprobación

Antes de ejecutar el plan:

- [ ] Análisis Enterprise revisado y aprobado
- [ ] Módulos Fase 1 confirmados
- [ ] Estrategia suscripción DEV/TEST/PROD acordada
- [ ] Acceso GitHub Enterprise verificado
- [ ] Infile: decidir timeline de contratación
- [ ] Confirmar que wizard, usuarios y localización siguen **bloqueados** hasta aprobación explícita

---

## Referencias

| Recurso | URL |
|---------|-----|
| Community → Enterprise | https://www.odoo.com/documentation/19.0/administration/on_premise/community_to_enterprise.html |
| Registro on-premise | https://www.odoo.com/documentation/19.0/administration/on_premise.html |
| Docker Hub odoo | https://hub.docker.com/_/odoo |
| Descarga Enterprise | https://www.odoo.com/page/download |
| Portal suscripciones | https://www.odoo.com/my/subscriptions |
| Localización RD | https://www.odoo.com/documentation/19.0/applications/finance/fiscal_localizations/dominican_republic.html |
| Repo Enterprise | https://github.com/odoo/enterprise (privado, requiere acceso) |
