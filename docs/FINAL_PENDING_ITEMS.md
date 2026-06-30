# Pendientes finales antes de Go-Live — Hellenia

**Fecha:** 2026-06-30  
**Entorno:** `hellenia_prod` — https://odoo.hellenia.cloud  
**Origen:** Fase 13.4 hardening + certificaciones 13.2–13.3

Esta es la **lista única consolidada** de pendientes para abrir el sistema a usuarios finales de Hellenia.

---

## P0 — Bloqueantes Go-Live

| # | Pendiente | Responsable | Estado |
|---|-----------|-------------|--------|
| P0-1 | **Rangos NCF reales DGII** (B01–B13 autorizados) | Hellenia + contador | Pendiente |
| P0-2 | **Usuarios operativos** según ROLE_MATRIX (no solo admin/it) | Justech + Hellenia | Pendiente |
| P0-3 | **SMTP corporativo** configurado y probado | Hellenia | Pendiente |
| P0-4 | **Limpiar facturas smoke P13.4** (INV/2026/00001–00003) | Justech | Pendiente |

---

## P1 — Requeridos para operación real

| # | Pendiente | Responsable | Estado |
|---|-----------|-------------|--------|
| P1-1 | **Catálogo de productos** (mobiliario, decoración, etc.) | Hellenia | Pendiente |
| P1-2 | **Clientes** — importar plantilla `clientes_import_template.csv` | Hellenia | Pendiente |
| P1-3 | **Proveedores** — importar plantilla `proveedores_import_template.csv` | Hellenia | Pendiente |
| P1-4 | **Logo y branding** PDF facturas / empresa | Hellenia | Pendiente |
| P1-5 | **Cuentas bancarias** y diarios banco operativos | Hellenia + contador | Pendiente |
| P1-6 | **Términos de pago** comerciales definitivos | Hellenia | Pendiente |
| P1-7 | **Política de inventario** (recepción, entrega, valuación) | Hellenia | Pendiente |

---

## P2 — Mejoras recomendadas (no bloqueantes)

| # | Pendiente | Responsable | Estado |
|---|-----------|-------------|--------|
| P2-1 | Ocultar "Aplicaciones" también para admin técnico en vista diaria | Justech | Opcional |
| P2-2 | Traducir nombres impuestos `l10n_do` vía etiquetas personalizadas | Contador | Opcional |
| P2-3 | Formato exportación DGII oficial (columnas exactas) — TD-008 | Justech roadmap | Opcional |
| P2-4 | Monitoreo/alertas automatizadas (disco, backups, health) | Infra | Parcial |
| P2-5 | Eliminar partners/productos smoke residuales | Justech | Tras P0-4 |

---

## Datos del cliente pendientes de carga

| Categoría | Plantilla / referencia | Prioridad |
|-----------|------------------------|-----------|
| Usuarios | `data/hellenia/templates/users_import_template.csv` | P0 |
| Productos | `data/hellenia/templates/productos_import_template.csv` | P1 |
| Clientes | `data/hellenia/templates/clientes_import_template.csv` | P1 |
| Proveedores | `data/hellenia/templates/proveedores_import_template.csv` | P1 |
| Rangos NCF | `data/hellenia/templates/ncf_rangos_dgii_template.csv` | P0 |
| Logo empresa | Configuración → Empresa | P1 |
| Bancos | Contabilidad → Diarios + cuentas banco | P1 |
| SMTP | `docs/SMTP_CONFIGURATION.md` | P0 |

---

## Completado en Fases 13.2–13.4 (no repetir)

- [x] Plan contable dominicano (`do`) cargado
- [x] ITBIS 18% — sin impuesto 15%
- [x] Módulos Justech 19.0.1.2.0 instalados
- [x] Reportes DGII 606/607/608 funcionales en español
- [x] Menú principal limpio (sin Tests, Discuss, Dashboards, duplicado Accounting)
- [x] WebSocket Traefik corregido
- [x] HTTPS `odoo.hellenia.cloud` operativo
- [x] Licencia EE registrada (Fase 13)
- [x] Idioma `es_DO` en usuarios actuales

---

## Orden de ejecución recomendado

1. Limpiar facturas smoke P13.4 (P0-4)  
2. Cargar rangos NCF DGII reales (P0-1)  
3. Configurar SMTP y probar envío (P0-3)  
4. Crear usuarios Hellenia con roles (P0-2)  
5. Importar maestros: productos, clientes, proveedores (P1)  
6. Configurar bancos y logo (P1)  
7. UAT final con usuarios reales  
8. Go-Live usuarios

---

**Última actualización:** 2026-06-30 — Fase 13.4
