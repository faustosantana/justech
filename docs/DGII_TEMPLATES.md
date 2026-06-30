# Plantillas oficiales DGII — Justech Localization RD

**Fase:** 17.4 — Repositorio oficial de plantillas  
**País:** República Dominicana (`do`)  
**Ruta:** `data/localizations/do/templates/`

---

## Origen

| Campo | Valor |
|-------|-------|
| Fuente oficial | [DGII — Formatos de Envío de Datos](https://dgii.gov.do/herramientas/formularios/formatoEnvioDatos/Paginas/default.aspx) |
| Entidad | Dirección General de Impuestos Internos (DGII) |
| Tipo de archivos | ZIP con herramientas Excel/macros oficiales |
| Fecha de descarga (UTC) | 2026-06-30T21:05:08Z |
| Total archivos | 33 |
| Inventario | `data/localizations/do/templates/templates.json` |

Los archivos se conservan **exactamente como fueron descargados**. No se modifican, renombran ni reempaquetan.

---

## Formatos principales incluidos

| Código | Archivo vigente (NG 07-2018) | Notas |
|--------|------------------------------|-------|
| **606** | `Formato-de-Envio-606-(NG-07-2018-y-05-2019).zip` | Compras — períodos desde mayo 2018 |
| **607** | `Formato-de-Envio-607-(NG-07-2018-y-05-2019).zip` | Ventas — períodos desde mayo 2018 |
| **608** | `Formato-de-Envio-608-(NG-07-2018-y-05-2019).zip` | NCF anulados — desde mayo 2018 |
| **609** | `Formato609-NG-7-18.zip` | Pagos al exterior — desde mayo 2018 |
| **623** | `FormatoenvioRetencionesEstado623.zip` | Retenciones del Estado |
| **ITBIS** | `FormatoExcelEnvioDatosITBIS.zip` | Envío de datos ITBIS |
| **Norma 2-05** | `FormatoExcelNORMA2-05RetencionesTerceros.zip` | Retenciones a terceros |

También se descargaron versiones **pre-mayo 2018**, formatos sectoriales (612–651, 629, 632 DIOR, minera IC1, etc.), instructivos y manuales ITBIS — ver `templates.json` completo.

### Libro de Ventas 987

**No encontrado** en la página oficial de Formatos de Envío de Datos al momento de la descarga. Si la DGII lo publica en otra sección, documentar la URL y agregarlo en una actualización futura.

---

## Versión e integridad

Cada entrada en `templates.json` incluye:

- `nombre` — etiqueta oficial en la página DGII
- `codigo` — código DGII (606, 607, ITBIS, NORM-2-05, etc.)
- `fecha_publicacion` — no publicada en la página (null)
- `fecha_modificacion` — fecha indicada por DGII en la página (`Modificado: DD/MM/YYYY`)
- `url_oficial` — enlace de descarga
- `sha256` — hash del archivo descargado
- `version` — referencia normativa inferida (ej. `NG-07-2018`, `pre-2018-05`)

Para verificar un archivo:

```bash
sha256sum "data/localizations/do/templates/Formato-de-Envio-606-(NG-07-2018-y-05-2019).zip"
```

Comparar con el valor en `templates.json`.

---

## Política de uso en Justech

> **NO utilizar estas plantillas para exportar directamente.**

Los módulos `justech_l10n_do_*` y exportadores Hellenia deben:

1. Leer la estructura de columnas, validaciones y reglas desde estas plantillas como **referencia normativa**.
2. Implementar generadores propios en `mappings/` y código de exportación.
3. Producir archivos de salida conformes a DGII **sin** distribuir ni ejecutar los Excel oficiales embebidos en el producto.

---

## Procedimiento de actualización

Cuando la DGII publique nuevas versiones:

### 1. Revisar la página oficial

Abrir: https://dgii.gov.do/herramientas/formularios/formatoEnvioDatos/Paginas/default.aspx

Comparar fechas `Modificado:` y nombres de archivo con `templates.json`.

### 2. Descargar archivos nuevos o actualizados

- Guardar en `data/localizations/do/templates/` **sin modificar** el contenido.
- Si un archivo reemplaza a uno anterior, **no borrar** el histórico sin registrar el cambio en git; preferir commit que muestre el reemplazo.

### 3. Regenerar `templates.json`

Actualizar metadatos: SHA256, `fecha_modificacion`, `url_oficial`, `version`.

### 4. Documentar

- Actualizar `fecha_descarga_utc` en `templates.json`.
- Actualizar esta guía con la fecha y resumen de cambios.
- Si cambian columnas o reglas, actualizar borradores en `data/localizations/do/mappings/`.

### 5. Validar exportadores

- Ejecutar pruebas de exportación en **TEST** (no PROD) contra la nueva referencia.
- No promover hasta aprobación explícita.

### 6. Commit

```bash
git add data/localizations/do/templates/ docs/DGII_TEMPLATES.md
git commit -m "Actualizar plantillas DGII — <fecha DGII>"
```

---

## Estructura del repositorio

```
data/localizations/do/
├── templates/          ← archivos oficiales DGII + templates.json
├── mappings/           ← mapeos Justech (futuro)
├── documentation/      ← notas complementarias
└── samples/            ← ejemplos de salida generados por Justech
```

---

## Entornos

Esta carpeta es **solo repositorio de referencia**. No se despliega en DEV, TEST ni PROD como addons Odoo.
