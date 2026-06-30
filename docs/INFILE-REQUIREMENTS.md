# Infile — Requisitos para eNCF (sin configurar aún)

**Estado:** Documentación únicamente — **no configurado** en DEV/TEST/PROD  
**Módulo Odoo:** `l10n_do_edi` (Enterprise)

---

## Qué es Infile

**Infile** es el proveedor de servicios de facturación electrónica (PSE) integrado oficialmente en Odoo para República Dominicana. Actúa como puente entre Odoo y la **DGII** para:

- Firma digital de XML ECF
- Transmisión a DGII
- Asignación/validación de **eNCF**

Fuente: [Documentación Odoo RD](https://www.odoo.com/documentation/19.0/applications/finance/fiscal_localizations/dominican_republic.html)

---

## Requisitos previos (empresa)

| Requisito | Responsable | Notas |
|-----------|-------------|-------|
| RNC activo DGII | Hellenia | RNC 133621282 |
| Registro como emisor electrónico | Hellenia + DGII | Trámite gubernamental |
| Rangos eNCF autorizados | DGII | Por tipo documento (E31–E34) |
| Contrato con Infile | Hellenia + Infile | Independiente de suscripción Odoo |
| Odoo Enterprise + `l10n_do_edi` | Justech | Licencia Odoo ya contratada |

---

## Credenciales Infile (necesarias en Odoo)

Configurar en: Contabilidad → Configuración → Facturación electrónica RD

| Campo Odoo | Descripción |
|------------|-------------|
| **Username** | Usuario API Infile |
| **Password** | Contraseña API |
| **Security Key** | Clave de seguridad Infile |
| **Llave** | Llave adicional Infile |
| **Web Service Environment** | Demo / Test / Production |

> Las credenciales las entrega **Infile** tras firmar contrato. No las provee Odoo.

---

## Ambientes Infile

| Ambiente | Infile requerido | Documentos legales | Uso Hellenia |
|----------|------------------|--------------------|--------------|
| **Demo** | No | No | Desarrollo local Odoo |
| **Test** | Sí | Sí (certificación) | UAT fiscal pre-producción |
| **Production** | Sí | Sí (válidos DGII) | Go-live |

---

## Costos (orientativos — confirmar con Infile)

| Concepto | Notas |
|----------|-------|
| Contrato Infile | Tarifa comercial Infile (no incluida en Odoo Enterprise) |
| Volumen documentos | Puede haber planes por cantidad de eNCF/mes |
| Odoo Enterprise | Suscripción `M260616306091776` — separada |
| DGII | Trámites rangos NCF/eNCF — sin costo Odoo/Infile directo |

**Acción pendiente:** Solicitar cotización formal a Infile antes de UAT fiscal en ambiente Test.

---

## Procedimiento de contratación (resumen)

1. **Hellenia** solicita alta como facturador electrónico ante DGII
2. Obtener rangos eNCF (E31, E32, E33, E34 según operación)
3. Contactar **Infile** (proveedor certificado en documentación Odoo)
4. Firmar contrato de servicios de facturación electrónica
5. Recibir credenciales API (Username, Password, Security Key, Llave)
6. En Odoo (futuro): instalar `l10n_do_edi` → configurar credenciales → ambiente Test
7. Certificación con DGII vía Infile
8. Cambiar a Production tras aprobación

---

## Documentos electrónicos soportados (Odoo oficial)

| Código | Tipo |
|--------|------|
| E31 | Factura de Crédito Fiscal Electrónica |
| E32 | Factura de Consumo Electrónica |
| E33 | Nota de Débito Electrónica |
| E34 | Nota de Crédito Electrónica |

---

## Configuración Odoo (cuando se autorice — NO ahora)

1. Instalar `l10n_do`, `l10n_do_edi`, `l10n_do_reports`
2. Configurar RNC en empresa
3. Crear rangos de documentos (desde autorización DGII)
4. Configurar diarios ventas con "Use Documents"
5. Ingresar credenciales Infile
6. Probar en Demo → Test → Production

---

## Bloqueo actual

- ⛔ No configurar credenciales Infile
- ⛔ No enviar documentos a DGII
- ⛔ No usar ambiente Production Infile
- ✅ Documentación y preparación arquitectónica completadas
