# Estrategia del Proyecto — Hellenia Odoo Enterprise RD

**Versión:** 3.0  
**Fecha:** 2026-06-30  
**Cliente:** Hellenia, S.R.L. — República Dominicana  
**Consultoría:** Justech

---

## Declaración de plataforma oficial

| Decisión | Valor |
|----------|-------|
| Producto | **Odoo 19 Enterprise On-Premise** |
| Infraestructura | VPS propio (`srv.hellenia.cloud`) |
| Código Enterprise | **Último paquete oficial** descargable del portal Odoo |
| Fuera de alcance estratégico | Perseguir funcionalidades exclusivas de **saas-19.3** u otras ramas SaaS |

> La documentación saas-19.3 puede usarse como **referencia orientativa** de capacidades futuras, pero **no** como requisito ni bloqueante del proyecto.

---

## Objetivo del proyecto

Convertir esta implementación en una **referencia profesional** de Odoo Enterprise para República Dominicana:

- Buenas prácticas Odoo Enterprise
- Mantenibilidad y upgrades futuros
- Cumplimiento DGII dentro de lo que entrega el producto on-premise
- Escalabilidad operativa
- Mínima deuda técnica
- **Cero modificaciones al core** (`enterprise/`, código Odoo)

---

## Hoja de ruta (12 fases)

| Fase | Nombre | Estado | Entregable principal |
|------|--------|--------|----------------------|
| **1** | Infraestructura | ✅ **Completa** | Docker, Traefik, backups, Git, DEV operativo |
| **2** | Enterprise | ✅ **Completa** | Imagen `hellenia-odoo:19-enterprise`, `web_enterprise` |
| **3** | Configuración funcional | 🔄 **En curso** | Empresa, usuarios, parámetros, maestros transversales |
| **4** | Localización RD | 🔄 **En curso** | `l10n_do`, `l10n_do_reports`, fiscalidad base |
| **5** | Ventas | ⏳ Pendiente | Ciclo comercial, facturación cliente |
| **6** | Compras | ⏳ Pendiente | Ciclo de abastecimiento |
| **7** | Inventario | ⏳ Pendiente | Almacenes, rutas, valorización |
| **8** | POS | ⏳ Pendiente | Punto de venta Hellenia |
| **9** | Contabilidad | ⏳ Pendiente | Cierres, conciliación, asientos |
| **10** | Reportes | ⏳ Pendiente | Fiscales DGII + gerenciales |
| **11** | Pruebas | ⏳ Pendiente | UAT, regresión, evidencia |
| **12** | Go Live | ⏳ Pendiente | TEST → PROD, licencia, cutover |

**Ambientes:** DEV (laboratorio) → TEST → PRODUCCIÓN. TEST y PROD no se modifican sin aprobación explícita.

---

## Política NCF y localización fiscal

### Lo que aceptamos

El comportamiento observado en **Odoo 19 Enterprise On-Premise** es la **línea base del proyecto**. No se reinvestiga periódicamente si Odoo “debería” implementar NCF de otra forma en ramas SaaS.

### Si encontramos una limitación real del producto

1. **Documentarla** con evidencia (captura, TC, referencia a módulo oficial).
2. **No modificar** el core ni `enterprise/`.
3. **No instalar** módulos de terceros (OCA, apps store no oficiales).
4. **Registrarla** en [GAP_ANALYSIS_RD.md](GAP_ANALYSIS_RD.md) como posible desarrollo Justech.
5. **Continuar** la implementación — la limitación **no detiene** el proyecto.

### Stack fiscal Etapa 1 (sin eNCF)

- `l10n_do` + `l10n_do_reports` (+ suite contable Enterprise)
- **Sin** `l10n_do_edi`, Infile ni comunicación electrónica DGII

---

## Política de módulos custom (Justech)

**No desarrollar custom** hasta completar las cuatro comprobaciones:

| # | Comprobación | Evidencia requerida |
|---|--------------|---------------------|
| 1 | La funcionalidad **no existe** en el producto desplegado | Prueba en DEV, búsqueda Apps, código en imagen |
| 2 | **No existe** configuración oficial (Ajustes, datos maestros, reglas) | Captura o checklist de configuración estándar |
| 3 | **No existe** módulo oficial Odoo que la cubra | Manifest, documentación 19.0 on-premise |
| 4 | **No existe** workaround oficial documentado | Procedimiento estándar Odoo o nota de consultor |

Solo entonces: proponer módulo `hellenia_*` o `justech_*` con diseño `_inherit`, sin tocar core.

Ver [CUSTOM_MODULE_GUIDE.md](CUSTOM_MODULE_GUIDE.md).

---

## Principios de consultoría (toda decisión)

1. **Estándar antes que custom** — Odoo oficial primero.
2. **Decisión justificada** — negocio + técnica Odoo en cada parámetro.
3. **Upgrade-safe** — nada que impida actualizar Enterprise en el futuro.
4. **Una fuente de verdad** — maestros definidos una vez.
5. **Trazabilidad** — venta → inventario → contabilidad → reporte.
6. **Documentar límites** — no ocultar brechas del producto.
7. **DEV como laboratorio** — promoción controlada a TEST/PROD.

---

## Documentos de referencia

| Documento | Uso |
|-----------|-----|
| [IMPLEMENTATION_MASTER_PLAN.md](IMPLEMENTATION_MASTER_PLAN.md) | Detalle por fase, checklists, criterios |
| [L10N_DO_TEST_PLAN.md](L10N_DO_TEST_PLAN.md) | Casos de prueba localización RD |
| [GAP_ANALYSIS_RD.md](GAP_ANALYSIS_RD.md) | Limitaciones conocidas / registro Justech |
| [NCF_IMPLEMENTATION.md](NCF_IMPLEMENTATION.md) | Alcance NCF tradicional |
| [L10N_DO_ARCHITECTURE_ANALYSIS.md](L10N_DO_ARCHITECTURE_ANALYSIS.md) | **Histórico** — investigación pre-pivot; no bloqueante |

---

## Fase actual y próximos pasos

**Fase activa:** 3 (Configuración funcional) + 4 (Localización RD) en paralelo controlado en DEV.

**Continuar sin bloqueos por investigación de versiones.**

1. Completar parametrización empresa y maestros (Fase 3).
2. Avanzar localización RD con pruebas del [plan funcional](L10N_DO_TEST_PLAN.md) (Fase 4).
3. Documentar limitaciones encontradas; no detener por G-01 u otras brechas hasta cerrar ciclo de implementación estándar.

---

**Mantenido por:** Justech — Consultoría Odoo Enterprise
