# Implementación logo oficial Hellenia

**Fase:** 13.7  
**Ambiente validado:** TEST  
**Commit:** `f918576`

---

## Objetivo

Incorporar el logo oficial de Hellenia, S.R.L. en el sistema para branding corporativo (empresa, PDFs, interfaz).

---

## Origen del asset

El logo se exportó en **solo lectura** desde producción (`res.company` id=1) antes de cualquier reparación en PROD. Dimensiones: **1600×381 px**, formato JPEG (~38 KB).

---

## Ubicación en repositorio

```
custom/hellenia_base/static/img/hellenia_logo.jpg
```

El módulo `hellenia_base` ya declara dependencia de branding; el asset queda versionado para despliegues reproducibles.

---

## Carga en Odoo (TEST)

Script de validación Fase 13.7:

1. Lee el archivo JPEG del módulo custom montado en `/mnt/custom-addons/hellenia_base/static/img/hellenia_logo.jpg`
2. Codifica en **base64** (requerido por campo `image_1920` de `res.company`)
3. Escribe en `res.company` (id=1) vía `write({'image_1920': b64})`

**Error inicial corregido:** guardar bytes crudos o usar extensión `.png` para contenido JPEG provocaba fallo silencioso. Solución: extensión `.jpg` + `base64.b64encode()`.

---

## Uso en PDFs

Los reportes de `hellenia_reports` referencian el layout `external_layout_hellenia`, que consume el logo de la compañía (`company.logo` / `image_1920`). Validado en generación de cotización, factura y nota crédito (attachments 81083, 87347, 86028).

---

## Promoción a producción

Tras aprobación y backup, el mismo archivo y script de carga se aplican en PROD con el commit certificado en TEST. No se modificó PROD durante Fase 13.7.
