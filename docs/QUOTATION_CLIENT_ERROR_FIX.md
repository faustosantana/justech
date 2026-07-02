# Corrección Error Clientes en Cotizaciones

**Fase:** 13.7  
**Ambiente corregido:** TEST (`hellenia_test`)  
**PROD:** Sin modificar

---

## 1. Síntoma reportado

Error al crear o buscar clientes desde el formulario de cotizaciones en la interfaz web Odoo.

---

## 2. Causa raíz

**No era un bug en `res.partner` ni en módulos Justech.**

La causa fue **adjuntos huérfanos en el filestore** de `hellenia_test`: registros `ir.attachment` apuntaban a archivos CSS de bundles de reportes (`web.report_assets_pdf.min.css`) que **no existían en disco**.

### Evidencia en logs TEST

```
FileNotFoundError: [Errno 2] No such file or directory: 
  '/var/lib/odoo/filestore/hellenia_test/bd/bd1dd8c28500b2a7b41c9e661ed13868ee9abd4b'
```

```
odoo.http: Exception during request handling.
  File ".../ir_attachment.py", line 930, in _to_http_stream
FileNotFoundError
```

### Cadena de impacto

1. Instalación/upgrade de `hellenia_reports` regeneró referencias de assets PDF
2. Archivos físicos no se crearon o se perdieron en el filestore
3. El navegador solicita `/web/content/...` para CSS de reportes
4. Odoo lanza 500 en requests HTTP
5. La UI de cotizaciones (autocompletado de partners, carga de assets) falla intermitentemente

### Prueba de descarte

Creación y búsqueda de partners vía shell **funcionan correctamente**:

```
CREATE_OK 318 Test Cliente P137
SEARCH_OK 1 [(318, 'Test Cliente P137')]
```

El problema era **infraestructura de assets/filestore**, no lógica de negocio.

---

## 3. Corrección aplicada (TEST)

Script: `scripts/phase13-7-validate-test.py`

| Paso | Acción |
|------|--------|
| 1 | Eliminar `ir.attachment` huérfanos (store_fname sin archivo en disco) |
| 2 | Regenerar bundles: `env['ir.qweb']._pregenerate_assets_bundles()` |
| 3 | Verificar partner create/search en contexto cotización |

### Resultado post-fix

```json
"partner_create_search": {
  "ok": true,
  "id": 335,
  "search_hits": 1
}
```

---

## 4. Prevención

| Medida | Descripción |
|--------|-------------|
| Política DEV→TEST→PROD | Instalar módulos de reportes primero en TEST |
| Post-upgrade | Ejecutar limpieza de adjuntos huérfanos |
| Monitoreo | Alertar en logs por `FileNotFoundError` en filestore |

---

## 5. Módulos Justech — sin cambios de código

`justech_l10n_do_base` / `res.partner` — restricción RNC dominicano opera correctamente; no requirió modificación para este incidente.
