# DGII Certification Readiness — Justech e-CF

**Entorno:** erp.justech.do / justech_dev  
**Producción (justgroup.app):** no tocada  
**Fecha:** 2026-07-12  

## Resumen ejecutivo

El motor técnico Justech e-CF está listo para **preparar** la certificación DGII.  
La **certificación DGII real** permanece **BLOQUEADA** por credenciales y certificado autorizados externos.  
No se declara PASS de cumplimiento DGII ni se envía a Producción DGII desde desarrollo.

---

## Qué está listo (técnico)

| Capacidad | Estado | Evidencia |
|---|---|---|
| XSDs oficiales e-CF 31–47 + auxiliares | PASS | `evidence/.../dgii/xsd/` + `dgii-source-register.md` |
| Generación XML local | PASS | `justech_ecf_xml` |
| Firma XML laboratorio (C14N + rsa-sha256 + enveloped) | PASS | `justech_ecf_signature` + smoke LAB_SIGN |
| Validación criptográfica de firma | PASS | verify OK / tamper FAIL |
| Cola, reintentos, dead-letter (mock) | PASS | `justech_ecf_queue` |
| Cliente DGII mock / cert bloqueado sin credenciales / prod gate | PASS | `justech_ecf_dgii` |
| Multiempresa: 1 empresa en `ecf_certification`, 3 en `traditional_ncf` | PASS | 4/4 empresas |
| API `/api/v1/ecf` (auth, scopes, rate limit, idempotencia, OpenAPI) | PASS | health/docs/receive |
| Recepción e-CF proveedor (XML, dup, ack local, sin auto-publicar) | PASS | inbound + API receive |
| Admin Center integración e-CF | PASS | producto Justech Fiscal → Justech e-CF |
| Gate Producción DGII | PASS | bloqueado sin aprobación explícita |

---

## Qué requiere credenciales DGII

- Usuario / contraseña / token del ambiente **certificación** (`certecf`)
- Credenciales de **prueba** (`testecf`) si se usan antes de certificación
- Semilla / autenticación según documentación oficial de Servicios e-CF
- Acceso autorizado al portal de certificación DGII

Sin esto: **no hay envío real**, solo mock.

---

## Qué requiere certificado autorizado

- Certificado digital P12/PFX **emitido para el RNC emisor**
- Cadena de confianza aceptada por DGII
- Contraseña del contenedor
- Validación de no vencimiento / RNC coincidente

El certificado de laboratorio en `/opt/odoo-dev/secrets/ecf-lab/`:

- sirve **solo** para pruebas criptográficas;
- **NO** certifica cumplimiento DGII;
- **NO** se usa para envío real;
- **NO** está en Git.

---

## Qué requiere intervención DGII

- Alta / habilitación del contribuyente en e-CF
- Asignación de ambiente de certificación
- Validación de casos exigidos por el proceso oficial
- Aprobación / rechazo de la certificación
- Paso a ambiente productivo (`ecf`) — **Gate de Producción Justech**

---

## Qué no puede certificarse localmente

- Aceptación oficial de XML por DGII
- TrackId / estados reales de recepción DGII
- Cumplimiento legal / fiscal de firma ante DGII
- Envío a Producción DGII
- Declarar “certificado DGII” sin resolución oficial

---

## Checklist de ambiente de certificación

1. [ ] Credenciales `certecf` recibidas y guardadas fuera de Git  
2. [ ] Certificado P12 autorizado cargado por empresa (encriptado)  
3. [ ] RNC emisor = RNC del certificado  
4. [ ] `fiscal_mode = ecf_certification` solo en empresa(s) autorizadas  
5. [ ] Endpoints oficiales validados (sin Producción):  
      - Semilla / autenticación  
      - Recepción e-CF  
      - Consulta estado / track  
6. [ ] Casos exigidos por Guía de Certificación DGII ejecutados  
7. [ ] Evidencias XML firmados + acuses guardadas en `/evidence/`  
8. [ ] Gate Producción: **aprobación explícita** antes de `dgii_environment=production`

---

## Criterios de aceptación (certificación)

- Todos los casos exigidos por DGII en estado aceptado  
- Firma válida según especificación oficial  
- Sin envíos a Producción durante el proceso  
- Evidencias reproducibles y rollback documentado  

## Gate de Producción (Justech)

Prohibido activar envío a `https://ecf.dgii.gov.do/ecf/...` sin:

1. Certificación DGII aprobada  
2. Aprobación explícita del propietario  
3. Backup + plan de rollback  
4. Validación post-despliegue en entorno controlado  

---

## Estado

**PASS TÉCNICO** (preparación)  
**BLOQUEADO POR CERTIFICACIÓN DGII** (credenciales / certificado / intervención DGII)
