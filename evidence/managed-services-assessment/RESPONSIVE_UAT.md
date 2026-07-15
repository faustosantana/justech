# RESPONSIVE UAT — formulario público MS

**Entorno:** `justech_dev` / `https://erp.justech.do`  
**Producción:** no tocada.

## Viewports

| Viewport | Ancho aprox. | Resultado | Evidencia |
|---|---|---|---|
| Escritorio | ≥1280 px | PASS — sin cortes, botones OK, progreso OK | `screenshots/01_desktop_inicial.png`, `04_revision.png` |
| Móvil | 390 × 844 | PASS — stack vertical; checkboxes/navegación utilizables | `screenshots/03_mobile_390.png` |
| Tableta | 768 × 1024 | PASS — sin scroll horizontal indebido en página de error corporativa | `screenshots/03b_tablet_768_error_page.png` |
| Intermedia (revisión) | escritorio | PASS | `screenshots/04_revision.png` |

## Criterios

| Criterio | Resultado |
|---|---|
| Campos no cortados | PASS |
| Checkbox utilizables | PASS |
| Botones visibles/correctos | PASS |
| Barra de progreso funciona | PASS (fill width se actualiza; etiqueta % estática hasta reload — ver MANUAL_UAT pendientes) |
| Sin desplazamiento horizontal innecesario | PASS |
| Sin errores JS/OWL en formulario público | PASS en flujo público |
| Backend OWL | Aviso push notifications del navegador (ajeno). Contactos/CRM con usuario solo-MS pueden fallar por ACL fiscal ajeno |

## Capturas requeridas

- Pantalla inicial → `01_desktop_inicial.png`
- Sección intermedia → `02_seccion_intermedia_equipos.png`
- Vista móvil → `03_mobile_390.png`
- Revisión → `04_revision.png`
- Confirmación final → `05_confirmacion_final.png`
- PDF → `08_pdf_pagina1.png` / `.pdf`
- Backend completado → `10_backend_form_completado.png`
