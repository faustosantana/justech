# RC-PURCHASE-FISCAL-P0 — Arquitectura Documentos Recibidos vs Emitidos

**Modo:** SOLO LECTURA / DISEÑO. Producción no modificada.  
**Fuentes:** `justech_pre_golive_ro` (dump pre Go-Live) + BD `justech` (PROD).  
**GL delta:** `0.00`

---

## 1. Comportamiento PRE vs POST (Compras)

| Aspecto | PRE Go-Live | POST Go-Live |
|---|---|---|
| Selector UI | `l10n_latam_document_type_id` → `l10n.latam.document.type` | `justech_do_document_type_id` → `justech.do.fiscal.document.type` (draft) |
| Diarios purchase `l10n_latam_use_documents` | `true` (5/5) | `false` (5/5) |
| Histórico vendor | 100% en latam | 100% en latam (`justech_do_document_type_id` = NULL) |
| Usage posted vendor | B01 + E31 (+ 2 anomalías B15/E31) | Idéntico |
| `in_refund` posted con tipo | 0 | 0 |
| B11/B13/B17 posted | 0 | 0 |
| AFS Adel B11/B13 (JUSTECH) | next 11 / 213 | next 11 / 213 (sin cambio) |
| Rango Justech B11/B13 (JUSTECH) | n/a (tabla no existía) | next 11 / 213 (= Adel) |

---

## 2. Grupo A — Documentos RECIBIDOS (registrar NCF/e-NCF del proveedor)

Modelo canónico: **`l10n.latam.document.type`** vía **`account.move.l10n_latam_document_type_id`**.  
Número: **`l10n_latam_document_number`** (manual).  
Company: catálogo global (sin `company_id` en latam).  
XML IDs en PROD: **vacíos** (registros sin `ir.model_data`).

Dominio PRE (motor `l10n_do_accounting`):
- Base: `internal_type in (invoice|debit_note|credit_note)` según move.
- + `l10n_do_ncf_type` según `_get_journal_ncf_types` / partner (`received`).
- Purchase: `_get_journal_codes()` → `[]` ⇒ **no filtra serie B vs E** (ambos visibles si el ncf_type aplica).
- Con partner `taxpayer`: incluye `fiscal`, `e-fiscal`, `special`, `governmental`, `e-governmental`, etc.

| Prefijo | Latam id | `l10n_do_ncf_type` | Consume seq | Consume rango | 606 | DGII/reportes | Uso hist. vendor |
|---|---|---|---|---|---|---|---|
| B01 | 1 | fiscal | No | No | Sí | Sí (vía latam/FDP) | 177 posted |
| B02 | 2 | consumer | No | No | Sí* | Sí* | 0 |
| B03 | 3 | debit_note | No | No | Sí* | Sí* | 0 |
| B04 | 4 | credit_note | No | No | Sí* | Sí* | 0 (`in_refund` sin tipo) |
| E31 | 13 | e-fiscal | No | No | Sí | Sí | 601 posted |
| E32 | 14 | e-consumer | No | No | Sí* | Sí* | 0 |
| E33 | 15 | e-debit_note | No | No | Sí* | Sí* | 0 |
| E34 | 16 | e-credit_note | No | No | Sí* | Sí* | 0 |
| E41 | 17 | e-informal | No | No | Sí* | Sí* | 0 |
| E43 | 18 | e-minor | No | No | Sí* | Sí* | 0 |
| E44 | 19 | e-special | No | No | Sí* | Sí* | 0 |
| E45 | 20 | e-governmental | No | No | Sí* | Sí* | 0 |
| E46 | 21 | e-export | No | No | Sí* | Sí* | 0 |
| E47 | 22 | e-exterior | No | No | Sí* | Sí* | 0 |

\*Incluibles según reglas del exporter 606 / FDP cuando el move es compra válida.

**Nota:** B14/B15/B16 como **recibidos** del proveedor (tipo latam) son posibles en dominio `received`; el histórico real casi no los usa. Hay 2 bills con type latam B15 pero NCF `E31…` (anomalía de dato, no arquitectura).

---

## 3. Grupo B — Documentos EMITIDOS por la empresa desde Compras

Motor Justech: `PURCHASE_NCF_PREFIXES = (B11, B13, B17)`.  
`auto_assign_on_post=True`, `is_purchase_document=True`.  
XML IDs: `justech_l10n_do_base.doc_type_b11|b13|b17`.

| Prefijo | Nombre | Modelo Justech | Rango activo PROD | Seq Adel (`account.fiscal.sequence`) PRE=POST | Último posted | Next esperado | Next config | Estado |
|---|---|---|---|---|---|---|---|---|
| B11 | Comprobante de Compras | `justech.do.fiscal.document.type` | JUSTECH 11–15 @11 | AFS id9 next=11 | (ninguno) | 11 | 11 | ✅ |
| B13 | Gastos Menores | idem | JUSTECH 213–217 @213 | AFS id8 next=213 | (ninguno) | 213 | 213 | ✅ |
| B17 | Pagos al Exterior | idem | ninguno | ninguno | (ninguno) | — | — | N/A |

**B14 / B15 / B16 NO son emitidos desde Compras** (evidencia):

| Prefijo | Side hist. posted | Justech flags | Conclusión |
|---|---|---|---|
| B14 | solo SALE | `is_sale_document` | Motor Ventas |
| B15 | solo SALE | `is_sale_document` | Motor Ventas |
| B16 | solo SALE | `is_sale_document` | Motor Ventas |

Incluirlos en “emitidos desde Compras” rompería la arquitectura DGII. Continuidad de B14–B16 se gobierna en Ventas (ya auditada; no tocada aquí).

**Advertencia pre-implementación (no es roto de continuidad posted):** draft `FP/2026/06/0001` (id 3140) tiene `l10n_latam_document_number=B1300000213` y AFS Gasto Menor #8; `number_next` Adel y Justech siguen en 213 (número aún no consumido). Antes de postear: alinear motor único para evitar doble consumo.

---

## 4. Matriz de continuidad (emitidos Compras) — sin diferencias ROJO

Ver `CONTINUITY_PURCHASE_ISSUED.csv`.

Criterio `next == histórico_posted + 1` (si no hay histórico posted ⇒ `next == sequence_start` del bloque autorizado Adel/Justech).

**Resultado:** 0 diferencias ROJO en B11/B13. Adel PRE ≡ Adel POST ≡ Justech POST para B11/B13 JUSTECH.

---

## 5. Impacto de una restauración correcta (diseño)

| Área | Impacto si se implementa el diseño |
|---|---|
| Ventas / Motor Fiscal emitido | Ninguno (sin cambios de rangos/secuencias/ventas) |
| 606 | Ninguno (sigue leyendo latam/FDP; se restaura capacidad de **capturar** recibidos) |
| 607/608/609/623 | Ninguno (ventas/otros; no se tocan exporters) |
| e-CF emisión | Ninguno (no crear rangos E ni emitir E31) |
| Histórico | Ninguno (no migrar M2O; latam intacto) |
| Pagos / conciliaciones | Ninguno |
| Garantías / fees | Ninguno |
| Multiempresa | Ninguno (catálogo latam/justech compartido; rangos por company) |
| Secuencias / rangos | Ninguno en fase restauración UI (no recalcular) |

---

## 6. Arquitectura objetivo (NO implementada)

```
VENTAS
  → Motor Fiscal Justech
  → justech_do_document_type_id (B01–B04, B12, B14–B16)
  → rangos/secuencias Justech
  → sin cambios

COMPRAS
  GRUPO A — RECIBIDOS
    → l10n_latam_document_type_id (B + E del catálogo latam)
    → l10n_latam_document_number manual
    → NO auto-assign Justech / NO consumir Adel al registrar recibidos
    → compat 606/histórico

  GRUPO B — EMITIDOS (B11, B13, B17)
    → justech_do_document_type_id + Motor Justech
    → consume rango/secuencia Justech
    → continuidad exacta ya verificada (11 / 213)
```

### Discriminación funcional (regla)

| Condición | Grupo | Campo tipo | NCF |
|---|---|---|---|
| Prefijo/tipo latam en set recibido (B01–B04, E31–E47, B14/B15/B16 recibidos) | A | latam | Manual |
| Prefijo Justech `is_purchase_ncf()` (B11/B13/B17) | B | Justech | Auto (si vacío) / validar manual |

`ncf_assignment_service` ya soporta: si `justech_do_ncf` informado → no consume; auto-assign solo si `doc.is_purchase_ncf()`.

---

## 7. Riesgos

| Riesgo | Severidad | Mitigación de diseño |
|---|---|---|
| Re-activar `l10n_latam_use_documents=true` sin apagar Adel | Alto | Solo si Adel no asigna en purchase; o mirror one-way Justech→latam sin consumir AFS |
| Doble motor en B13 draft 3140 | Medio | Gate pre-post: un solo asignador; no tocar número hasta regla clara |
| Mostrar solo Justech B-types para recibidos | Alto (estado actual) | Restaurar selector latam B+E para Grupo A |
| Tratar B14–B16 como purchase-issued | Alto | Clasificar como Ventas; no crear flujos “emitidos desde Compras” |
| Migrar histórico a Justech types | Alto | Prohibido |
| Tocar 606–623 / XML IDs / Studio | Alto | Fuera de alcance |

---

## 8. Lista exacta de cambios mínimos (posterior, con aprobación)

1. **Vista `account.move` (purchase draft):**  
   - Grupo A: visible `l10n_latam_document_type_id` + `l10n_latam_document_number` con dominio latam B+E recibidos.  
   - Grupo B: visible `justech_do_document_type_id` limitado a B11/B13/B17 + NCF Justech.  
2. **Regla de UI/compute** para modo recibido vs emitido (sin nuevo modelo de tipo).  
3. **Assignment:** garantizar que compras recibidas **nunca** lean `justech_do_use_ncf` para auto-asignar; solo Grupo B.  
4. **Journals:** decidir explícitamente si `l10n_latam_use_documents` vuelve a `true` solo para purchase **con** Adel assignment desactivado en post, **o** forzar visibilidad latam por attrs sin depender del flag (evitar doble emisión).  
5. **Gate draft B13 3140** antes de cualquier post productivo con Motor Justech.  
6. **Tests:** bill E31 recibido (sin rango), bill B01 recibido, bill B11/B13 emitido (consume next 11/213), ventas B01 intactas, export 606 smoke sobre histórico.  
7. **No hacer:** crear tipos E Justech, rangos E, secuencias E, recálculo next, cambios 606–623, migración histórica, cambiar XML IDs, Studio, layouts de reporte.
