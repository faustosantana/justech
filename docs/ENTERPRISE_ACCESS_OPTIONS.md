# Opciones de acceso al código Odoo Enterprise

**Suscripción Hellenia:** `M260616306091776`  
**Contexto:** On-premise / self-hosted, Docker Community + addons Enterprise  
**Fecha:** 2026-06-30

> Solo afirmaciones respaldadas por documentación oficial Odoo 19.0, salvo donde se indique verificación en portal.

---

## Resumen ejecutivo

| Opción | ¿Oficial? | Estado Hellenia | Recomendación |
|--------|-----------|-----------------|---------------|
| **A. Descarga portal Odoo** | ✅ Sí | **Pendiente verificación usuario** | **✅ Camino principal ahora** |
| **B. GitHub `odoo/enterprise`** | ✅ Sí | ❌ Bloqueado (`faustosantana` sin acceso repo) | Secundario / largo plazo |
| **C. Ticket soporte Odoo** | ✅ Sí | No abierto | Si portal no habilita descarga |
| **D. Odoo Support / Account Manager** | ✅ Sí | No contactado | Escalamiento contractual |
| **E. Partner Odoo** | ✅ Sí (si aplica) | Justech — verificar rol partner | Solo si somos partner oficial |

**Decisión Hellenia:** Proceder con **descarga oficial desde el portal** (`odoo.com/page/download`) mientras se resuelve GitHub en paralelo. **No bloquear el proyecto** esperando GitHub.

---

## Fuentes oficiales

| Documento | URL |
|-----------|-----|
| Source install — Archive / Git | https://www.odoo.com/documentation/19.0/administration/on_premise/source.html |
| Packaged installers | https://www.odoo.com/documentation/19.0/administration/on_premise/packages.html |
| Bugfix updates (descarga) | https://www.odoo.com/documentation/19.0/administration/on_premise/update.html |
| Download page | https://www.odoo.com/page/download |
| On-premise / suscripción | https://www.odoo.com/documentation/19.0/administration/on_premise.html |

---

## A. Descarga oficial desde portal Odoo

### Qué documenta Odoo

> *"There are two ways to obtain the source code of Odoo: as a **ZIP archive** or through **Git**."*  
> *"**Enterprise edition:** Odoo download page"*  
> — [Source install](https://www.odoo.com/documentation/19.0/administration/on_premise/source.html)

> *"It is **required to be logged in as a paying on-premise customer or partner** to download the Enterprise packages."*  
> — [Packaged installers](https://www.odoo.com/documentation/19.0/administration/on_premise/packages.html)

> *"The central download page is https://www.odoo.com/page/download. If you see a **'Buy' link** for the Odoo Enterprise download, make sure you are logged into Odoo.com with the **same login that is linked to your Odoo Enterprise subscription**."*  
> — [Bugfix updates](https://www.odoo.com/documentation/19.0/administration/on_premise/update.html)

> *"Alternatively, you can use the **unique download link** that was included with your Odoo Enterprise **purchase confirmation email**."*  
> — [Bugfix updates](https://www.odoo.com/documentation/19.0/administration/on_premise/update.html)

### ¿Nuestra suscripción self-hosted permite descarga directa?

| Criterio oficial | Hellenia `M260616306091776` |
|------------------|----------------------------|
| Producto | Odoo Enterprise on-premise (confirmado en análisis previo) |
| Requisito | Cuenta odoo.com vinculada a la suscripción |
| Edición | Self-hosted / on-premise — **sí aplica** según documentación |
| Verificación práctica | Usuario debe ver botón **Download** (no **Buy**) en Enterprise → Sources Odoo 19 |

**La documentación no lista excepciones** que impidan descarga a suscriptores on-premise activos. Si el portal muestra *Buy*, el requisito que falta es casi siempre: **sesión odoo.com incorrecta** o suscripción no *In Progress*.

### Procedimiento preparado (sin ejecutar E1)

Ver [E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md](E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md) y [E0.6c-ENTERPRISE-DELIVERY-FLOW.md](E0.6c-ENTERPRISE-DELIVERY-FLOW.md).

Scripts:

| Script | Uso |
|--------|-----|
| `download-enterprise-portal.sh` | Descarga desde URL temporal (Flujo A) |
| `receive-enterprise-archive.sh` | Recibe archivo vía Cursor (Flujo B) |
| `validate-enterprise-archive.sh` | Validación exhaustiva + `--report` |
| `e1a-portal-pipeline.sh` | `--validate-only` o `--execute` (tras aprobación) |
| `extract-enterprise-portal.sh` | Extrae a `enterprise/` |

### Ventajas / desventajas

| Ventajas | Desventajas |
|----------|-------------|
| No depende de GitHub | Actualización manual (nuevo tarball) |
| Procedimiento oficial equivalente | Sin `git log` / commit hash nativo |
| Funciona con Docker + volumen | Descarga requiere login humano en portal |
| Misma `addons_path` que Git | Enlace portal expira; usuario entrega URL o archivo a Cursor |

---

## B. GitHub `odoo/enterprise`

### Qué documenta Odoo

> *"git clone ... https://github.com/odoo/enterprise.git"* (rama alineada con Community)  
> — [Source install](https://www.odoo.com/documentation/19.0/administration/on_premise/source.html)

El acceso al repo privado se otorga vinculando **GitHub Users** en la suscripción en [odoo.com/my/subscriptions](https://www.odoo.com/my/subscriptions).

### Estado Hellenia (2026-06-30)

| Verificación | Resultado |
|--------------|-----------|
| SSH VPS → GitHub | ✅ Autentica como `faustosantana` |
| `git ls-remote odoo/enterprise` | ❌ `Repository not found` |
| Interpretación oficial GitHub | Sin permiso de lectura al repo privado |

### ¿Depende de la vinculación Odoo?

**Sí**, según procedimiento documentado en portal Odoo y foros oficiales:

1. Suscripción Enterprise activa (*In Progress*)
2. Username GitHub exacto en **GitHub Users** de la suscripción
3. Aceptar invitación GitHub si Odoo la envía (equipo/org)
4. Propagación 5–30 minutos

**Nota:** La cuenta **odoo.com** para descargas y el usuario **GitHub** vinculado pueden ser personas distintas; ambos deben estar correctamente asociados a la suscripción.

### Ventajas / desventajas

| Ventajas | Desventajas |
|----------|-------------|
| `git pull` para parches | Bloqueado actualmente |
| Trazabilidad commit | Depende de propagación Odoo→GitHub |
| Alineado con UPGRADE-PATH largo plazo | Segundo canal de soporte si falla |

---

## C. Ticket con Odoo (Helpdesk)

### Cuándo usarlo

| Situación | Ticket |
|-----------|--------|
| Portal muestra *Buy* con suscripción activa | ✅ Sí |
| Descarga falla tras login correcto | ✅ Sí |
| GitHub Users configurado >24h sin acceso | ✅ Sí |
| UUID duplicado en registro BD | ✅ Sí |

### Qué solicitar

- Habilitar descarga Enterprise Odoo **19 Sources** para `M260616306091776`
- O confirmar username GitHub autorizado y reenviar invitación
- Referencia: self-hosted Docker, República Dominicana

### URL

https://www.odoo.com/help (o enlace *Send a support ticket* en mensajes de error on-premise)

---

## D. Odoo Support / Account Manager

Escalamiento si:

- Ticket sin respuesta en plazo contractual
- Discrepancia contrato vs portal (usuarios, edición, vigencia)
- Success Pack / soporte incluido en contrato Justech

**No sustituye** la descarga por portal si esta está habilitada.

---

## E. Partner Odoo

| Escenario | Aplica |
|-----------|--------|
| Justech es **Odoo Partner** con acceso partner | Puede tener vías adicionales |
| Justech es **cliente final** vía contrato Hellenia | Usar portal + soporte estándar |

La documentación indica que partners también descargan desde el portal estando logueados.

---

## Comparativa decisión

```
                    ┌─────────────────────┐
                    │ ¿Portal Download    │
                    │ visible (no Buy)?   │
                    └──────────┬──────────┘
                          Sí   │   No
                    ┌──────────┴──────────┐
                    ▼                     ▼
           DESCARGA PORTAL          ¿GitHub repo OK?
           (recomendado)                  │
                                    Sí   │   No
                                    ▼    ▼
                                  GIT   TICKET ODOO
                                        (+ portal cuando habiliten)
```

---

## Camino recomendado para Hellenia

### Fase inmediata (E1a-revised)

1. **Usuario:** Login odoo.com → descargar **Odoo 19 → Enterprise → Sources** (o copiar enlace temporal)
2. **Usuario:** Entregar **URL temporal** o **archivo adjunto** a Cursor — **sin SCP al VPS** ([E0.6c](E0.6c-ENTERPRISE-DELIVERY-FLOW.md))
3. **Cursor:** `e1a-portal-pipeline.sh --validate-only`
4. **Usuario:** Aprobar explícitamente E1a portal
5. **Cursor:** `e1a-portal-pipeline.sh --execute` → DEV `web_enterprise`
6. **Paralelo:** Seguir gestionando acceso GitHub para actualizaciones futuras

### Fase largo plazo

- Migrar a `git pull` en `enterprise/` cuando GitHub funcione
- Mantener `extract-enterprise-portal.sh` como fallback documentado en UPGRADE-PATH

---

## Lo que NO depende del código Enterprise (continúa en paralelo)

| Área | Estado |
|------|--------|
| Módulos custom (esqueletos) | ✅ |
| Docker / compose / healthchecks | ✅ |
| `addons_path` / config | ✅ |
| Scripts backup / restore / deploy | ✅ |
| Documentación licenciamiento / upgrade | ✅ |
| Análisis l10n RD | Ver [L10N-RD-READINESS.md](L10N-RD-READINESS.md) |
| DEV Community operativo | ✅ |
| TEST / PROD | Sin tocar |

---

## Referencias internas

- [E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md](E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md)
- [E0.6c-ENTERPRISE-DELIVERY-FLOW.md](E0.6c-ENTERPRISE-DELIVERY-FLOW.md)
- [E0.6-GITHUB-ENTERPRISE.md](E0.6-GITHUB-ENTERPRISE.md)
- [E1-CHECKLIST.md](E1-CHECKLIST.md)
- [UPGRADE-PATH.md](UPGRADE-PATH.md)
