# Análisis técnico — Odoo 19 para Hellenia

**Fecha:** 2026-06-30  
**Alcance:** Infraestructura DEV/TEST (Community Edition)  
**Producción:** Permanece en Odoo 18 hasta aprobación explícita  
**Decisión infra:** ✅ Migrar DEV y TEST a `odoo:19.0-20260619`  
**Decisión fiscal:** ⚠️ eNCF completo requiere Odoo Enterprise (`l10n_do_edi`)

---

## Resumen ejecutivo

| Área | Resultado | Riesgo |
|------|-----------|--------|
| PostgreSQL 17 | ✅ Compatible | Bajo |
| Traefik | ✅ Compatible | Ninguno |
| Docker Compose | ✅ Compatible | Bajo |
| `l10n_do` (Community) | ✅ v2.0 presente en Odoo 19 | Bajo |
| NCF (papel) | ⚠️ Secuencias definidas; uso legal limitado en Community | Medio (negocio) |
| eNCF / DGII (electrónico) | ❌ No en Community; requiere Enterprise + Infile | Alto (si e-factura obligatoria) |
| Migración infra 18→19 | ✅ Viable en DEV/TEST (BD mínima: solo `base`) | Bajo |

---

## 1. PostgreSQL 17 + Odoo 19

**Veredicto: ✅ COMPATIBLE**

- Odoo 19 requiere **PostgreSQL 13+** como mínimo ([documentación oficial](https://www.odoo.com/documentation/saas-19.2/administration/on_premise/source.html)).
- PostgreSQL **17** es la versión ya desplegada en DEV, TEST y producción (`postgres:17-alpine`).
- No se requiere cambio de versión de PostgreSQL para la migración.
- Los volúmenes de datos PG existentes se reutilizan sin `pg_upgrade`.

**Estado actual Hellenia:**

| Ambiente | Imagen PG | Versión detectada |
|----------|-----------|-------------------|
| DEV | `postgres:17-alpine` | 17.x |
| TEST | `postgres:17-alpine` | 17.x |
| PROD | `postgres:17-alpine` | 17.x |

---

## 2. Traefik

**Veredicto: ✅ COMPATIBLE — sin cambios**

Traefik actúa como reverse proxy TLS independiente de la versión de Odoo.

- Labels actuales (`traefik.enable`, `Host()`, `entrypoints=websecure`, `certresolver=letsencrypt`) permanecen válidos.
- Puerto backend Odoo: **8069** (sin cambio en Odoo 19).
- No se modifica `traefik-traefik-1` ni su configuración.
- SSL Let's Encrypt en `dev.hellenia.cloud` y `test.hellenia.cloud` no se ve afectado.

---

## 3. Docker Compose

**Veredicto: ✅ COMPATIBLE — cambio mínimo**

Único cambio requerido en `docker-compose.yml`:

```yaml
# Antes
image: odoo:18.0-20260619   # o odoo:18

# Después
image: odoo:19.0-20260619
```

| Componente | Cambio |
|------------|--------|
| Servicio `odoo` | Tag de imagen |
| Servicio `db` | Sin cambio |
| Volúmenes | Sin cambio |
| Redes | Sin cambio |
| Labels Traefik | Sin cambio |
| Variables `.env` | Sin cambio |

**Tag seleccionado:** `odoo:19.0-20260619`  
- Misma fecha de build que la imagen 18 actual (paridad de parches nightly).
- **No** se usa `latest` ni `19` (floating tags).

---

## 4. Localización oficial República Dominicana

### Módulos oficiales Odoo para RD

| Módulo | Edición | Odoo 18 CE | Odoo 19 CE | Odoo 19.3+ Enterprise/Online |
|--------|---------|------------|------------|-------------------------------|
| `l10n_do` | Community | ✅ v2.0 | ✅ v2.0 | ✅ |
| `l10n_do_edi` | Enterprise | ❌ | ❌ | ✅ |
| `l10n_do_reports` | Enterprise | ❌ | ❌ | ✅ |
| `l10n_do_check_printing` | Enterprise | ❌ | ❌ | ✅ |

**Fuente:** [Documentación Odoo RD](https://www.odoo.com/documentation/saas-19.3/applications/finance/fiscal_localizations/dominican_republic.html), repositorio `odoo/odoo` branch 19.0.

### Contenido de `l10n_do` v2.0 (Community)

- Catálogo de cuentas alineado DGII/NIIF
- Impuestos ITBIS (18%, 16%, 0%, exento), retenciones ISR/ITBIS, propina 10%
- Posiciones fiscales preconfiguradas
- Secuencias NCF predefinidas (B01, B02, B14, etc.)
- Moneda DOP (RD$)

**Nota oficial del manifest:**

> *"Esta localización, aunque posee las secuencias para NCF, las mismas no pueden ser utilizadas sin la instalación de módulos de terceros o desarrollo adicional."*

Hellenia usa **solo módulos oficiales** → en Community Edition, NCF operativo completo **no está disponible** ni en 18 ni en 19.

---

## 5. Confirmación `l10n_do` en Odoo 19

**Veredicto: ✅ FUNCIONA en Odoo 19 Community**

Verificación en imagen `odoo:19.0-20260619`:

- Módulo presente en `/usr/lib/python3/dist-packages/odoo/addons/l10n_do/`
- Versión manifest: **2.0** (idéntica a Odoo 18)
- Instalable vía Apps → "Dominican Republic" o `-i l10n_do`
- Sin dependencias Enterprise

**Prueba post-migración:** script `scripts/validate-odoo19.sh` verifica presencia del módulo.

---

## 6. Soporte oficial NCF, eNCF, DGII

### NCF (Comprobantes Fiscales en papel)

| Aspecto | Community 19 | Enterprise 19.3+ |
|---------|--------------|------------------|
| Secuencias NCF | ✅ Preconfiguradas | ✅ |
| Emisión legal NCF | ❌ Requiere dev/terceros | ⚠️ Parcial vía eNCF |
| Formatos PDF DGII | ❌ | ✅ Con `l10n_do_edi` |

### eNCF (Comprobantes Fiscales Electrónicos)

| Aspecto | Community 19 | Enterprise 19.3+ |
|---------|--------------|------------------|
| Módulo `l10n_do_edi` | ❌ No incluido | ✅ |
| Proveedor certificado | — | Infile |
| Tipos E31/E32/E33/E34 | — | ✅ |
| Envío XML a DGII | — | ✅ vía Infile |
| Ambiente Demo/Test/Prod | — | ✅ |

### DGII (cumplimiento tributario)

| Funcionalidad | Community 19 | Enterprise 19.3+ |
|---------------|--------------|------------------|
| Plan contable DGII | ✅ `l10n_do` | ✅ |
| Tasas ITBIS/retenciones | ✅ | ✅ |
| Campo RNC empresa | ✅ | ✅ |
| Reportes fiscales RD | ❌ `l10n_do_reports` | ✅ |
| Facturación electrónica ECF | ❌ | ✅ |
| Estado DGII en factura | ❌ | ✅ |

**Conclusión fiscal:** La migración a Odoo 19 **Community** mejora la plataforma base pero **no desbloquea** e-factura DGII. Para eNCF oficial se requiere **Odoo Enterprise** + cuenta **Infile** + rangos autorizados DGII.

---

## 7. Mejoras Odoo 19 vs 18 para República Dominicana

### Mejoras generales Odoo 19 (aplican a Hellenia)

- Python 3.12 en imagen Docker (mejor rendimiento)
- ORM y UI refinados (Odoo 19 release)
- Compatibilidad PG 17 nativa con benchmarks positivos
- Soporte extendido de versión mayor

### Mejoras específicas RD

| Mejora | Odoo 18 CE | Odoo 19 CE | Odoo 19.3 Enterprise |
|--------|------------|------------|----------------------|
| `l10n_do` v2.0 | ✅ | ✅ (sin cambio manifest) | ✅ |
| e-Factura Infile | ❌ | ❌ | ✅ **Nuevo** |
| Reportes DGII | ❌ | ❌ | ✅ **Nuevo** |
| Cheques RD | ❌ | ❌ | ✅ **Nuevo** |
| E31/E32/E33/E34 | ❌ | ❌ | ✅ **Nuevo** |

**Para Hellenia en Community:** el beneficio fiscal RD es **equivalente** entre 18 y 19. El salto fiscal real ocurre solo con Enterprise.

---

## 8. Evaluación de riesgos

### Riesgos infraestructura (DEV/TEST)

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| Fallo migración BD 18→19 | Baja | Backup previo; BD solo tiene `base` |
| Incompatibilidad PG 17 | Muy baja | PG 17 ya validado con Odoo 18 |
| Rotura Traefik/SSL | Muy baja | Labels sin cambio |
| Impacto producción | Nula | `/docker/odoo-pecv` no se toca |

### Riesgos fiscales (negocio)

| Riesgo | Impacto | Nota |
|--------|---------|------|
| Sin eNCF en Community | Alto a mediano plazo | Evaluar Enterprise antes de go-live fiscal |
| NCF papel no operativo | Medio | Planificar Enterprise o alternativa aprobada |
| Wizard prematuro | Medio | **Bloqueado** hasta DEV/TEST estables |

### Decisión

✅ **Proceder con migración infra DEV/TEST** — riesgo técnico bajo.  
⛔ **No migrar producción** — pendiente aprobación.  
⛔ **No ejecutar wizard** — pendiente estabilización Odoo 19.

---

## 9. Imagen Docker seleccionada

```
odoo:19.0-20260619
```

| Tag | Fecha build | Uso |
|-----|-------------|-----|
| `19.0-20260619` | 2026-06-22 | **DEV/TEST (seleccionado)** |
| `19.0-20260609` | 2026-06-09 | Alternativa |
| `19` / `latest` | Floating | **Prohibido** |

---

## 10. Referencias

- [Odoo 19 — Requisitos PostgreSQL](https://www.odoo.com/documentation/saas-19.2/administration/on_premise/source.html)
- [Localización RD — Odoo 19.3 docs](https://www.odoo.com/documentation/saas-19.3/applications/finance/fiscal_localizations/dominican_republic.html)
- [Odoo Docker Hub — tags 19.0](https://hub.docker.com/_/odoo)
- [Forum Odoo — l10n_do documentos soportados](https://www.odoo.com/forum/help-1/l10n-do-documentos-soportados-nueva-localizacion-republica-dominicana-302531)
- Manifest Community: `odoo/odoo` branch `19.0` → `addons/l10n_do/__manifest__.py`

---

## Anexo: estado pre-migración (2026-06-30)

| URL | Versión | HTTP |
|-----|---------|------|
| https://dev.hellenia.cloud | 18.0-20260619 | 200 |
| https://test.hellenia.cloud | 18.0-20260619 | 200 |
| https://odoo-pecv.srv1784296.hstgr.cloud | 18.x | 303 |
