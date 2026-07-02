# Fase 28 — Diagnóstico Vista previa / Imprimir (PROD 18:31 UTC)

## Ventana analizada
- **Servidor:** https://odoo.hellenia.cloud (`hellenia_prod`)
- **Rango logs:** 2026-07-02 18:29:00 – 18:35:00 UTC (2:29–2:35 PM America/Santo_Domingo)
- **Usuario:** `it@justech.do` (uid 5), IP `170.244.42.35`
- **Factura:** INV/2026/00006 (id 132)

## Respuestas (7 puntos)

### 1. Petición exacta a las ~18:31 UTC
**Ninguna petición de Vista previa ni Imprimir llegó al servidor.**

Peticiones reales del usuario en esa ventana:
- `GET /odoo/accounting/9/invoicing/132` (18:29:53, 18:30:06)
- `POST .../account.move/web_read` (carga formulario)
- `POST .../account.move/button_cancel` (18:31:23)
- `POST .../ir.actions.report/get_valid_action_reports` (18:31:34)
- `POST .../account.move/get_extra_print_items` (18:31:34 — abrir menú Imprimir)

**Ausentes:** `preview_invoice`, `action_print_pdf`, `/report/download`, `/my/invoices/132`

### 2. Botón que originó el error
**Vista previa** e **Imprimir** (cabecera del formulario). El cliente Odoo abortó la acción **antes** de enviar RPC.

### 3. Controlador ejecutado
**Ninguno** para esos botones. No hubo `call_button` ni render QWeb.

### 4. Action report utilizado
**Ninguno** en ese intento.

### 5. Template QWeb renderizado
**Ninguno** en ese intento.

### 6. Excepción exacta
**No hay traceback Python/QWeb en servidor.** El error es **validación JavaScript del formulario**:

- Mensaje UI: *"Faltan algunos campos obligatorios"*
- Origen Odoo: `Missing required fields` (`web/static/src/model/relational_model/record.js`)
- Campo bloqueante: `justech_do_ncf_void_reason`
- Condición errónea en vista `justech_l10n_do_ncf.view_move_form_justech_do_ncf`:
  `required="state == 'posted' and justech_do_ncf and not justech_do_ncf_voided"`
- Factura 132: `state=posted`, `justech_do_ncf=B0200009905`, `justech_do_ncf_void_reason` vacío → formulario inválido.

**Nota:** `hellenia_ux` (que corrige este `required`) está **desinstalado** en producción.

### 7. Por qué el navegador muestra error sin petición al servidor
Odoo 19 valida campos obligatorios del registro en el **cliente OWL** antes de ejecutar botones `type="object"`. Si el formulario es inválido, muestra el toast y **no llama** a `/web/dataset/call_button/...`.

El menú **Imprimir → Invoice PDF** usa otro flujo (`get_extra_print_items` + descarga de reporte) que no exige guardar/validar el formulario completo, por eso puede funcionar mientras fallan Vista previa e Imprimir.

## Corrección aplicada
- Módulo: `hellenia_reports` 19.0.1.5.7
- Archivo: `views/account_move_ncf_void_reason_fix.xml`
- Acción: `invisible` cuando no anulado + `required=0` (validación de motivo solo al anular vía `action_void_ncf`)
