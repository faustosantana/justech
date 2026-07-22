# Matriz de compatibilidad — Autollenado plantillas oficiales

**Generado:** 2026-06-24T20:52:55.130453+00:00
**Expediente QA:** DGII-CCC-PEEX-2026-0005
**Batch:** `/var/jaios/expedientes/8ebfa281-cd3c-4017-8e47-c572a79d84b2/_autofill_qa_20260624_192857`

## Resumen

| Métrica | Valor |
|---------|-------|
| Total plantillas indexadas | 61 |
| PASS | 51 |
| PARTIAL | 2 |
| FAIL | 8 |
| Stubs usados | **0** (bloqueados) |

## Validación obligatoria (8 muestras)

| Formulario | Plantilla | Fuente | DOCX | PDF | Completados | Faltantes | Formato | Estado |
|---|---|---|---|---|---|---|---|---|
| SNCC F.033 | SNCC_F033_Of_Economica.docx | M365 / SharePoint | sí | sí | 3 | 1 | sí | **PASS** |
| SNCC F.034 | SNCC_F034_Presentacion_de_Oferta.docx | M365 / SharePoint | sí | sí | 3 | 1 | sí | **PASS** |
| SNCC F.042 | SNCC_F042_Informacion_Oferente.docx | M365 / SharePoint | sí | sí | 4 | 1 | sí | **PASS** |
| SNCC F.047 | SNCC_F047_Autorizacion_Fabricante.docx | M365 / SharePoint | sí | sí | 3 | 1 | sí | **PASS** |
| SNCC F.009 | SNCC_F009_Convocatoria_a_LPN.docx | M365 / SharePoint | sí | sí | 11 | 1 | sí | **PASS** |
| SNCC F.010 | SNCC_F010_Convocatoria_LPI.docx | M365 / SharePoint | sí | sí | 11 | 1 | sí | **PASS** |
| Carta (D.058) | SNCC_D_058_Carta_de_Disponibilidad.docx | M365 / SharePoint | sí | sí | 5 | 1 | sí | **PASS** |
| Declaración | — | — | — | — | — | — | — | **Sin plantilla en biblioteca** |

## Los 8 FAIL — causa raíz detallada

### 1. PLANTILLA.SNCC_C025_CONTRATO_EJECUCION_DE_SERVICIO_CONSULTOR

- **Formulario:** `PLANTILLA.SNCC_C025_CONTRATO_EJECUCION_DE_SERVICIO_CONSULTOR`
- **Tipo:** contrato
- **Fuente:** Sin plantilla oficial
- **Causa raíz:** Plantilla indexada en biblioteca pero bytes no disponibles: caché vacía, portal DGCP sin este archivo, SharePoint devuelve 401 (OAuth desconectado).
- Falta plantilla: sí
- No es DOCX: no
- Plantilla corrupta: no
- Requiere OCR/conversión: no
- **Acción:** 1) Reconectar OAuth M365 (fausto@justech.do). 2) Sincronizar repositorio Plantillas. 3) Ejecutar bootstrap_m365_template_cache. 4) Si no está en DGCP público, cargar manualmente a caché oficial.

### 2. SNCC.P066

- **Formulario:** `SNCC.P066`
- **Tipo:** sncc_pliego
- **Fuente:** Sin plantilla oficial
- **Causa raíz:** Plantilla indexada en biblioteca pero bytes no disponibles: caché vacía, portal DGCP sin este archivo, SharePoint devuelve 401 (OAuth desconectado).
- Falta plantilla: sí
- No es DOCX: no
- Plantilla corrupta: no
- Requiere OCR/conversión: no
- **Acción:** 1) Reconectar OAuth M365 (fausto@justech.do). 2) Sincronizar repositorio Plantillas. 3) Ejecutar bootstrap_m365_template_cache. 4) Si no está en DGCP público, cargar manualmente a caché oficial.

### 3. SNCCP.PROV.F040

- **Formulario:** `SNCCP.PROV.F040`
- **Tipo:** proveedor
- **Fuente:** Sin plantilla oficial
- **Causa raíz:** Plantilla indexada en biblioteca pero bytes no disponibles: caché vacía, portal DGCP sin este archivo, SharePoint devuelve 401 (OAuth desconectado).
- Falta plantilla: sí
- No es DOCX: no
- Plantilla corrupta: no
- Requiere OCR/conversión: no
- **Acción:** 1) Reconectar OAuth M365 (fausto@justech.do). 2) Sincronizar repositorio Plantillas. 3) Ejecutar bootstrap_m365_template_cache. 4) Si no está en DGCP público, cargar manualmente a caché oficial.

### 4. SNCCP.PROV.F041

- **Formulario:** `SNCCP.PROV.F041`
- **Tipo:** proveedor
- **Fuente:** Sin plantilla oficial
- **Causa raíz:** Plantilla indexada en biblioteca pero bytes no disponibles: caché vacía, portal DGCP sin este archivo, SharePoint devuelve 401 (OAuth desconectado).
- Falta plantilla: sí
- No es DOCX: no
- Plantilla corrupta: no
- Requiere OCR/conversión: no
- **Acción:** 1) Reconectar OAuth M365 (fausto@justech.do). 2) Sincronizar repositorio Plantillas. 3) Ejecutar bootstrap_m365_template_cache. 4) Si no está en DGCP público, cargar manualmente a caché oficial.

### 5. Requiere plantilla DOCX editable

- **Formulario:** `CARTA.CARTA_COMPROMISO_2024_11X8_5`
- **Tipo:** carta
- **Fuente:** Sin plantilla oficial (PDF)
- **Causa raíz:** Plantilla indexada como PDF — el motor requiere DOCX oficial editable. No se descargó bytes (OAuth M365 desconectado; no hay caché local).
- Falta plantilla: sí
- No es DOCX: sí
- Plantilla corrupta: no
- Requiere OCR/conversión: sí
- **Acción:** 1) Obtener versión DOCX oficial o convertir manualmente a DOCX editable. 2) Subir a biblioteca M365 / ejecutar bootstrap con OAuth. 3) Re-ejecutar autollenado.

### 6. PLANTILLA.DATOS_PARA_EL_LLENADO_DE_FORMULARIOS

- **Formulario:** `PLANTILLA.DATOS_PARA_EL_LLENADO_DE_FORMULARIOS`
- **Tipo:** datos_empresa
- **Fuente:** Sin plantilla oficial
- **Causa raíz:** Plantilla indexada en biblioteca pero bytes no disponibles: caché vacía, portal DGCP sin este archivo, SharePoint devuelve 401 (OAuth desconectado).
- Falta plantilla: sí
- No es DOCX: no
- Plantilla corrupta: no
- Requiere OCR/conversión: no
- **Acción:** 1) Reconectar OAuth M365 (fausto@justech.do). 2) Sincronizar repositorio Plantillas. 3) Ejecutar bootstrap_m365_template_cache. 4) Si no está en DGCP público, cargar manualmente a caché oficial.

### 7. CARTA.CARTA_COMPROMISO

- **Formulario:** `CARTA.CARTA_COMPROMISO`
- **Tipo:** carta
- **Fuente:** Sin plantilla oficial
- **Causa raíz:** Plantilla indexada en biblioteca pero bytes no disponibles: caché vacía, portal DGCP sin este archivo, SharePoint devuelve 401 (OAuth desconectado).
- Falta plantilla: sí
- No es DOCX: no
- Plantilla corrupta: no
- Requiere OCR/conversión: no
- **Acción:** 1) Reconectar OAuth M365 (fausto@justech.do). 2) Sincronizar repositorio Plantillas. 3) Ejecutar bootstrap_m365_template_cache. 4) Si no está en DGCP público, cargar manualmente a caché oficial.

### 8. Requiere plantilla DOCX editable

- **Formulario:** `PLANTILLA.FORMULARIO_RED_PDF`
- **Tipo:** administrativo
- **Fuente:** Sin plantilla oficial (PDF)
- **Causa raíz:** Plantilla indexada como PDF — el motor requiere DOCX oficial editable. No se descargó bytes (OAuth M365 desconectado; no hay caché local).
- Falta plantilla: sí
- No es DOCX: sí
- Plantilla corrupta: no
- Requiere OCR/conversión: sí
- **Acción:** 1) Obtener versión DOCX oficial o convertir manualmente a DOCX editable. 2) Subir a biblioteca M365 / ejecutar bootstrap con OAuth. 3) Re-ejecutar autollenado.


## Los PARTIAL — causa raíz detallada

### SNCC_D039_Liquidacion_Contrato.docx

- **Campos críticos pendientes:** Indicar Nombre del Adjudicatario, Logo de la dependencia gubernamental
- **Causa raíz:** Plantilla oficial OK; campos de etapa post-adjudicación sin datos en expediente: Indicar Nombre del Adjudicatario. Campos no mapeados: 2.
- Requiere mapeo manual: sí
- **Acción:** Completar manualmente campos de adjudicación/contrato o mapear aliases; no aplica en etapa de oferta.

### SNCC_D040_Ejecucion_GFCC.docx

- **Campos críticos pendientes:** No. de Contrato, Nombre del Adjudicatario, Logo de la dependencia gubernamental, Dia, Mes y Año en Letras y Números, Tipo de Contrato y Denominación, Vencimiento de la Garantia en Letras y Números, Motivaciones del Contrato en cuanto a incumplimientos
- **Causa raíz:** Plantilla oficial OK; campos de etapa post-adjudicación sin datos en expediente: No. de Contrato, Nombre del Adjudicatario. Campos no mapeados: 1.
- Requiere mapeo manual: sí
- **Acción:** Completar manualmente campos de adjudicación/contrato o mapear aliases; no aplica en etapa de oferta.


## Matriz completa (61 plantillas)

| Formulario | Tipo | Plantilla | Fuente | DOCX | PDF | Det. | Compl. | Falt. | No mapeados | Formato | Estado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CARTA.CARTA_COMPROMISO | carta | Sin plantilla oficial | Sin plantilla oficia | no | no | 0 | 0 | 0 | 0 | no | **FAIL** |
| CARTA.CARTA_COMPROMISO_2024_11X8_5 | carta | Requiere plantilla DOCX editable | Sin plantilla oficia | no | no | 0 | 0 | 0 | 0 | no | **FAIL** |
| PLANTILLA.DATOS_PARA_EL_LLENADO_DE_FORMULARIOS | datos_empresa | Sin plantilla oficial | Sin plantilla oficia | no | no | 0 | 0 | 0 | 0 | no | **FAIL** |
| PLANTILLA.FORMULARIO_RED_PDF | administrativo | Requiere plantilla DOCX editable | Sin plantilla oficia | no | no | 0 | 0 | 0 | 0 | no | **FAIL** |
| PLANTILLA.SNCC_C025_CONTRATO_EJECUCION_DE_SERVICIO_CONSULTOR | contrato | Sin plantilla oficial | Sin plantilla oficia | no | no | 0 | 0 | 0 | 0 | no | **FAIL** |
| SNCC.P066 | sncc_pliego | Sin plantilla oficial | Sin plantilla oficia | no | no | 0 | 0 | 0 | 0 | no | **FAIL** |
| SNCCP.PROV.F040 | proveedor | Sin plantilla oficial | Sin plantilla oficia | no | no | 0 | 0 | 0 | 0 | no | **FAIL** |
| SNCCP.PROV.F041 | proveedor | Sin plantilla oficial | Sin plantilla oficia | no | no | 0 | 0 | 0 | 0 | no | **FAIL** |
| SNCC.D039 | contrato | SNCC_D039_Liquidacion_Contrato.docx | M365 / SharePoint | sí | sí | 18 | 16 | 2 | 2 | sí | **PARTIAL** |
| SNCC.D040 | sncc_documento | SNCC_D040_Ejecucion_GFCC.docx | M365 / SharePoint | sí | sí | 22 | 12 | 7 | 1 | sí | **PARTIAL** |
| PLANTILLA.SNCC_PCC_002_ACCESIBILIDAD_UNIVERSAL | general_dgcp | SNCC_PCC_002_Accesibilidad_Universa… | M365 / SharePoint | sí | sí | 4 | 4 | 0 | 1 | sí | **PASS** |
| SNCC.D014 | sncc_documento | SNCC_D014_Invitacion_Ofertas.docx | M365 / SharePoint | sí | sí | 14 | 9 | 4 | 1 | sí | **PASS** |
| SNCC.D016 | sncc_documento | SNCC_D016_Respuesta_Oferentes.docx | M365 / SharePoint | sí | sí | 13 | 8 | 4 | 1 | sí | **PASS** |
| SNCC.D020 | sncc_documento | SNCC_D020_Errores_u_Omisiones.docx | M365 / SharePoint | sí | sí | 12 | 8 | 3 | 1 | sí | **PASS** |
| SNCC.D027 | sncc_documento | SNCC_D027_Orden_Compra.docx | M365 / SharePoint | sí | sí | 19 | 11 | 6 | 1 | sí | **PASS** |
| SNCC.D028 | sncc_documento | SNCC_D028_Orden_Servicios.docx | M365 / SharePoint | sí | sí | 18 | 11 | 5 | 1 | sí | **PASS** |
| SNCC.D029 | sncc_documento | SNCC_D029_Recepcion_Bienes.docx | M365 / SharePoint | sí | sí | 10 | 5 | 3 | 1 | sí | **PASS** |
| SNCC.D030 | sncc_documento | SNCC_D030_Recepcion_Servicios.docx | M365 / SharePoint | sí | sí | 7 | 5 | 1 | 1 | sí | **PASS** |
| SNCC.D031 | sncc_documento | SNCC_D031_Recepcion_Provisional_Obr… | M365 / SharePoint | sí | sí | 18 | 10 | 8 | 1 | sí | **PASS** |
| SNCC.D032 | sncc_documento | SNCC_D032_Recepcion_Definitiva_Obra… | M365 / SharePoint | sí | sí | 21 | 12 | 9 | 1 | sí | **PASS** |
| SNCC.D038 | sncc_documento | SNCC_D038_Garantia_GFC.docx | M365 / SharePoint | sí | sí | 4 | 3 | 1 | 2 | sí | **PASS** |
| SNCC.D041 | sncc_documento | SNCC_D041_Devolución_GSO.docx | M365 / SharePoint | sí | sí | 11 | 6 | 3 | 1 | sí | **PASS** |
| SNCC.D043 | consultoria | SNCC_D043_Experiencia_Consultor.docx | M365 / SharePoint | sí | sí | 3 | 2 | 1 | 2 | sí | **PASS** |
| SNCC.D044 | consultoria | SNCC_D044_Enfoque_y_Metodologia.docx | M365 / SharePoint | sí | sí | 3 | 2 | 1 | 2 | sí | **PASS** |
| SNCC.D045 | consultoria | SNCC_D045_Curriculo_Personal.docx | M365 / SharePoint | sí | sí | 3 | 2 | 1 | 6 | sí | **PASS** |
| SNCC.D048 | consultoria | SNCC_D048_Experiencia_Profesional_P… | M365 / SharePoint | sí | sí | 4 | 3 | 1 | 2 | sí | **PASS** |
| SNCC.D049 | consultoria | SNCC_D049_Experiencia_contratista.d… | M365 / SharePoint | sí | sí | 5 | 3 | 1 | 1 | sí | **PASS** |
| SNCC.D051 | sncc_documento | SNCC_D051_Designacion_Agente.docx | M365 / SharePoint | sí | sí | 4 | 3 | 1 | 2 | sí | **PASS** |
| SNCC.D052 | sncc_documento | SNCC_D052_Aceptacion_Agente.docx | M365 / SharePoint | sí | sí | 4 | 3 | 1 | 1 | sí | **PASS** |
| SNCC.D054 | sncc_documento | SNCC_D054_Invitación_a_presentar_Of… | M365 / SharePoint | sí | sí | 14 | 9 | 4 | 1 | sí | **PASS** |
| SNCC.D058 | carta | SNCC_D_058_Carta_de_Disponibilidad.… | M365 / SharePoint | sí | sí | 7 | 5 | 1 | 1 | sí | **PASS** |
| SNCC.F009 | sncc_formulario | SNCC_F009_Convocatoria_a_LPN.docx | M365 / SharePoint | sí | sí | 16 | 11 | 1 | 1 | sí | **PASS** |
| SNCC.F010 | sncc_formulario | SNCC_F010_Convocatoria_LPI.docx | M365 / SharePoint | sí | sí | 16 | 11 | 1 | 1 | sí | **PASS** |
| SNCC.F011 | sncc_formulario | SNCC_F011_Convocatoria_LR.docx | M365 / SharePoint | sí | sí | 16 | 11 | 1 | 1 | sí | **PASS** |
| SNCC.F012 | sncc_formulario | SNCC_F012_Convocatoria_CP.docx | M365 / SharePoint | sí | sí | 17 | 11 | 4 | 1 | sí | **PASS** |
| SNCC.F013 | sncc_formulario | SNCC_F013_Convocatoria_CM.docx | M365 / SharePoint | sí | sí | 16 | 10 | 4 | 1 | sí | **PASS** |
| SNCC.F015 | sncc_formulario | SNCC_F015_Interesados.docx | M365 / SharePoint | sí | sí | 8 | 5 | 1 | 1 | sí | **PASS** |
| SNCC.F017 | sncc_formulario | SNCC_F017_Aclaraciones.docx | M365 / SharePoint | sí | sí | 8 | 5 | 1 | 1 | sí | **PASS** |
| SNCC.F018 | sncc_formulario | SNCC_F018_Adendas_Enmiendas.docx | M365 / SharePoint | sí | sí | 7 | 5 | 1 | 1 | sí | **PASS** |
| SNCC.F019 | sncc_formulario | SNCC_F019_Participantes.docx | M365 / SharePoint | sí | sí | 10 | 6 | 3 | 1 | sí | **PASS** |
| SNCC.F021 | sncc_formulario | SNCC_F021_Estudio_de_Precios.docx | M365 / SharePoint | sí | sí | 9 | 6 | 2 | 1 | sí | **PASS** |
| SNCC.F022 | sncc_formulario | SNCC_F022_Lugares_Ocupados.docx | M365 / SharePoint | sí | sí | 10 | 6 | 3 | 1 | sí | **PASS** |
| SNCC.F033 | oferta_economica | SNCC_F033_Of_Economica.docx | M365 / SharePoint | sí | sí | 5 | 3 | 1 | 6 | sí | **PASS** |
| SNCC.F034 | sncc_formulario | SNCC_F034_Presentacion_de_Oferta.do… | M365 / SharePoint | sí | sí | 4 | 3 | 1 | 2 | sí | **PASS** |
| SNCC.F035 | oferta_tecnica | SNCC_F035_Soporte_Tecnico.docx | M365 / SharePoint | sí | sí | 4 | 3 | 1 | 2 | sí | **PASS** |
| SNCC.F036 | sncc_formulario | SNCC_F036_Equipos_Oferente.docx | M365 / SharePoint | sí | sí | 4 | 3 | 1 | 2 | sí | **PASS** |
| SNCC.F037 | sncc_formulario | SNCC_F037_Personal_Oferente.docx | M365 / SharePoint | sí | sí | 4 | 3 | 1 | 2 | sí | **PASS** |
| SNCC.F042 | sncc_formulario | SNCC_F042_Informacion_Oferente.docx | M365 / SharePoint | sí | sí | 5 | 4 | 1 | 1 | sí | **PASS** |
| SNCC.F046 | sncc_formulario | SNCC_F046_Impugnaciones.docx | M365 / SharePoint | sí | sí | 7 | 5 | 1 | 1 | sí | **PASS** |
| SNCC.F047 | sncc_formulario | SNCC_F047_Autorizacion_Fabricante.d… | M365 / SharePoint | sí | sí | 4 | 3 | 1 | 4 | sí | **PASS** |
| SNCC.F050 | sncc_formulario | SNCC_F050_Convocatoria_SO.docx | M365 / SharePoint | sí | sí | 16 | 11 | 1 | 1 | sí | **PASS** |
| SNCC.F055 | sncc_formulario | SNCC_F055_Convocatoria_Procedimient… | M365 / SharePoint | sí | sí | 16 | 10 | 4 | 1 | sí | **PASS** |
| SNCC.F056 | sncc_formulario | SNCC_F_056_Formulario_de_Entrega_de… | M365 / SharePoint | sí | sí | 4 | 3 | 1 | 2 | sí | **PASS** |
| SNCC.F057 | sncc_formulario | SNCC_F_057_Informe_de_Homologación_… | M365 / SharePoint | sí | sí | 7 | 4 | 3 | 4 | sí | **PASS** |
| SNCC.F060 | sncc_formulario | SNCC_F_060_Portada_Expediente_admin… | M365 / SharePoint | sí | sí | 3 | 2 | 0 | 2 | sí | **PASS** |
| SNCC.F061 | sncc_formulario | SNCC_F061_Portada_Licitacion_Restri… | M365 / SharePoint | sí | sí | 3 | 2 | 0 | 2 | sí | **PASS** |
| SNCC.F062 | sncc_formulario | SNCC_F062_Portada_Sorteo_de_Obras.d… | M365 / SharePoint | sí | sí | 3 | 2 | 0 | 2 | sí | **PASS** |
| SNCC.F063 | sncc_formulario | SNCC_F063_Portada_Comparacion_de_Pr… | M365 / SharePoint | sí | sí | 3 | 2 | 0 | 2 | sí | **PASS** |
| SNCC.F064 | sncc_formulario | SNCC_F064_Portada_Compra_Menor.docx | M365 / SharePoint | sí | sí | 3 | 2 | 0 | 2 | sí | **PASS** |
| SNCC.F065 | sncc_formulario | SNCC_F065_Portada_Compra_Directa.do… | M365 / SharePoint | sí | sí | 3 | 2 | 0 | 2 | sí | **PASS** |
| SNCC.P059 | sncc_pliego | SNCC.P059 Pliego Estándar de Condic… | M365 / SharePoint | sí | sí | 0 | 0 | 0 | 41 | sí | **PASS** |