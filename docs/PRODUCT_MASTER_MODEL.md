# Modelo Maestro de Productos — Hellenia

**Fase:** 8  
**Ambiente:** DEV  
**Fecha:** 2026-06-30  
**Estado bloque:** **PASS CON OBSERVACIONES**

---

## 1. Principio rector

**El catálogo completo NO está cargado.** Esta fase define el **modelo maestro** y la estructura para importación futura.

---

## 2. Categorías oficiales

Jerarquía bajo `Inventario` (Fase 3.5):

| # | Categoría |
|---|-----------|
| 1 | Mobiliario |
| 2 | Espejos |
| 3 | Lámparas |
| 4 | Esculturas |
| 5 | Relojería |
| 6 | Pinturas |
| 7 | Dibujos y litografías |
| 8 | Tapisería |
| 9 | Cristalería |
| 10 | Plata |
| 11 | Vajillas |

**Comportamiento:** mayoría piezas únicas; algunos repetidos (pares). Ver `config/company/inventory_categories.yaml`.

---

## 3. Campos del modelo maestro

| Campo Odoo | Uso Hellenia | Obligatorio import |
|------------|--------------|-------------------|
| `default_code` | Código interno (Código) | ✅ |
| `name` | Descripción | ✅ |
| `categ_id` | Categoría oficial | ✅ |
| `type` | `consu` (Goods) | ✅ |
| `is_storable` | `True` para inventario | ✅ |
| `standard_price` | Costo | Opcional |
| `list_price` | Precio venta | Opcional |
| `barcode` | Código barras | Pendiente catálogo |
| `weight` / dimensiones | Logística | Opcional |
| `image_1920` | Fotografía | Opcional |
| `description_sale` | Observaciones | Opcional |
| `supplier_ids` | Código proveedor | Fase importación |
| `product_tag_ids` | Etiquetas | Pendiente |
| `taxes_id` | ITBIS 18% venta | Automático por defecto |

---

## 4. Atributos y variantes

| Elemento | Estado DEV | Recomendación |
|----------|------------|---------------|
| Atributos (`product.attribute`) | 8 estándar Odoo | Minimizar variantes |
| Variantes | No usadas en piloto | Solo si par/talla real |
| Marcas | No configuradas | Pendiente — `product.brand` o etiqueta |
| Fabricantes | No configurados | Campo libre o partner |

---

## 5. Unidades de medida

| UoM | Uso |
|-----|-----|
| Unidades | Default piezas |
| Otros (14 UoM sistema) | Disponibles según necesidad |

---

## 6. Clasificación

| Tipo | Configuración |
|------|---------------|
| Fiscal | ITBIS 18% venta / compra vía impuestos producto |
| Inventario | `consu` + `is_storable=True` |
| Contable | Cuentas por categoría — pendiente validación contador |

---

## 7. Plantilla importación

Archivo: `data/import/product_import_template.csv`  
Especificación: `config/company/product_import.yaml`

```text
Código, Descripción, Categoría, Costo, Precio, Existencia, Fotografía, Observaciones
```

**Método recomendado:** Importación nativa Odoo (Inventario → Productos → Importar).

---

## 8. Productos en DEV (piloto / prueba)

| Código | Nombre | Categoría | Origen |
|--------|--------|-----------|--------|
| PHASE4-TEST-001 | Producto prueba Fase 4 | Espejos | E2E Fase 4 |
| UAT-PILOT-PROD-001 | Producto Piloto UAT | Espejos | Fase 8 |

**Total productos DEV:** 3

---

## 9. Pendientes

| Item | Prioridad |
|------|-----------|
| Catálogo completo Excel/CSV de Hellenia | P0 (pre-UAT o durante UAT) |
| Política fotografías (resolución, naming) | P2 |
| Códigos de barras | P2 |
| Marcas y fabricantes | P2 |
| Limpiar categorías legacy Fase 3 | P3 |

---

## 10. Validación

```
Estado: PASS CON OBSERVACIONES
Causa: catálogo no cargado por diseño
Impacto: UAT puede usar productos piloto; catálogo real pendiente Hellenia
Prioridad: P0 entrega plantilla Excel poblada por Hellenia
Propuesta: sesión de mapeo columnas antes de import masivo
```

---

## 11. Referencias

- `config/company/product_import.yaml`
- `config/company/inventory_categories.yaml`
- [INVENTORY_CONFIGURATION.md](INVENTORY_CONFIGURATION.md)
