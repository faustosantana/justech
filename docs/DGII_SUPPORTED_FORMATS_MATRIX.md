# Matriz de formatos DGII soportados — Justech Localization RD

**Fase:** 17.5  
**Última actualización:** 2026-06-30

Leyenda de **estado exportador**:

| Estado | Significado |
|--------|-------------|
| `listo_estructura` | Columnas mapeadas; faltan solo campos Odoo documentados |
| `requiere_campos_faltantes` | Bloqueado por campos fiscales no implementados |
| `requiere_investigacion_contable` | Requiere definición de reglas contables/operativas |
| `sectorial` | Aplica solo a industrias específicas |
| `no_aplica` | Instructivo, manual o instalador — no es formato de datos |
| `version_historica` | Solo períodos hasta abril 2018 |

---

## Formatos core (prioridad Hellenia)

| Código | Versión vigente | Mapeo JSON | Columnas | Macros | Estado exportador | Notas |
|--------|-----------------|------------|----------|--------|-------------------|-------|
| **606** | NG 07-2018 / 05-2019 | `dgii_606.json` | 25 | No | `requiere_campos_faltantes` | Compras — facturas proveedor |
| **607** | NG 07-2018 / 05-2019 | `dgii_607.json` | 25 | No | `requiere_campos_faltantes` | Ventas — facturas cliente |
| **608** | NG 07-2018 / 05-2019 | `dgii_608.json` | 5 | No | `requiere_campos_faltantes` | NCF anulados |
| **609** | NG 07-2018 | `dgii_609.json` | 15 | **Sí** | `requiere_investigacion_contable` | Pagos al exterior |
| **623** | Actual | `dgii_623.json` | 8 | No | `requiere_investigacion_contable` | Retenciones del Estado |
| **ITBIS** | v1.0 | `dgii_itbis.json` | 7+8 | No | `requiere_campos_faltantes` | Adelantos LOCAL + IMPORTACION |
| **Norma 2-05** | v1.0 | `dgii_norma_2_05.json` | 8 | No | `requiere_campos_faltantes` | Retenciones ITBIS a terceros |

---

## Versiones históricas (pre-mayo 2018)

| Código | Archivo | Estado | Acción recomendada |
|--------|---------|--------|-------------------|
| 606 | `Formato606.zip` | `version_historica` | Usar mapeo NG; columnas reducidas |
| 606-GOB | `Formato606Gubernamental.zip` | `version_historica` | Variante gubernamental — investigar si aplica a Hellenia |
| 607 | `Formato607.zip` | `version_historica` | 9 columnas vs 25 NG |
| 608 | `Formato608.zip` | `version_historica` | Estructura similar a NG |
| 609 | `PagosalExterior609.zip` | `version_historica` | Reemplazado por NG 7-18 |

---

## Formatos sectoriales y especializados

| Código | Sector | Columnas | Macros | Estado | ¿Aplica Hellenia? |
|--------|--------|----------|--------|--------|-------------------|
| **612** | Compras divisas | 10 | No | `sectorial` | No — entidades reguladas cambio |
| **613** | Ventas divisas | 10 | No | `sectorial` | No |
| **615** | Reembolsos seguros | 11 | No | `sectorial` | No — aseguradoras |
| **616** | Comisiones aseguradoras/ARS | 11 | No | `sectorial` | No |
| **629** | Siniestros vehículos | 5 | No | `sectorial` | No — aseguradoras |
| **632** | DIOR relacionados | 41 | Sí | `sectorial` | Investigar si hay partes relacionadas |
| **641** | Retención ganancia capital | 7 | No | `sectorial` | Posible si hay operaciones de activos |
| **642** | Crédito impuestos exterior | 10 | No | `sectorial` | Si hay operaciones internacionales |
| **643** | Boletos transporte | 13 | Sí | `sectorial` | No — líneas aéreas/marítimas |
| **644** | Compra combustible | 15 | No | `sectorial` | Solo distribuidores combustible |
| **645** | Venta combustible | 15 | No | `sectorial` | Solo distribuidores combustible |
| **647** | Sujetos obligados no financieros | 26 | No | `sectorial` | No — reporte AML/estadístico |
| **648** | Tabaco (cigarrillos) | 3 | No | `sectorial` | No |
| **649** | Alcohol (ISC) | 21 | No | `sectorial` | No — industria bebidas |
| **650** | Minerales ventas | 13 | No | `sectorial` | No — minería IC1 |
| **651** | Minerales cobros | 16 | No | `sectorial` | No — minería IC1 |
| **IC1** | Paquete minera | 13–16 | No | `sectorial` | No |

---

## Documentación y herramientas (no exportables)

| Archivo | Tipo | Estado |
|---------|------|--------|
| `InstructivoEnvioSiniestrosVehiculos(629).zip` | Instructivo | `no_aplica` |
| `InstructivoFormatoExcelEnvioDatosITBIS.zip` | Instructivo | `no_aplica` — consultar para reglas ITBIS |
| `ManualenviodatosITBIS.zip` | Manual | `no_aplica` |
| `Instalacion_ValidadorEntidadadFinanciera.zip` | Instalador Windows | `no_aplica` — Norma 13-2011 entidades financieras |

---

## Libro de Ventas 987

| Estado | Nota |
|--------|------|
| **No descargado** | No encontrado en [página oficial DGII](https://dgii.gov.do/herramientas/formularios/formatoEnvioDatos/Paginas/default.aspx) |

---

## Resumen ejecutivo

| Categoría | Cantidad |
|-----------|----------|
| ZIP analizados | 33 |
| Formatos con Excel de datos | 28 |
| Mapeos JSON completos | 7 |
| Listos para implementar exportador (estructura) | 7 |
| Bloqueados por campos faltantes | 5 (606, 607, 608, ITBIS LOCAL, Norma 2-05) |
| Requieren investigación contable | 2 (609, 623) |
| Sectoriales / no aplican a Hellenia | 17+ |
| No encontrado (987) | 1 |

---

## Prioridad de implementación sugerida

1. **606 + 607 + 608** — reportes mensuales obligatorios para contribuyentes con NCF.
2. **Norma 2-05** — complementa retenciones ITBIS (motor Fase 18 ya en TEST).
3. **ITBIS LOCAL** — adelantos de compras locales.
4. **623** — si Hellenia recibe retenciones del Estado (GOB-5 en catálogo).
5. **609** — si hay proveedores de servicios en el exterior.
6. **ITBIS IMPORTACION** — requiere integración aduanera o captura manual.
