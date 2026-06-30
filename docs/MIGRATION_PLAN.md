# Plan de Migración — Go-Live Hellenia

**Estado:** Diseñado — **NO EJECUTADO**  
**Estrategia:** Nueva BD Odoo 19 (`hellenia_prod`) + corte desde `odoo-pecv` (Odoo 18)

---

## 1. Alcance

| Incluye | Excluye |
|---------|---------|
| Nueva instancia Odoo 19 Enterprise | Migración in-place Odoo 18→19 en odoo-pecv |
| Módulos Justech MVP | POS |
| Parametrización Fase 8 | Datos históricos completos (evaluar por fase) |
| Import maestros acordados | CRM/Helpdesk |

---

## 2. Orden de migración

| Fase | Actividad | Dependencia |
|------|-----------|-------------|
| M1 | Backup final odoo-pecv | — |
| M2 | Desplegar hellenia-prod (BD vacía) | M1 |
| M3 | Instalar módulos + parametrización | M2 |
| M4 | Licencia Enterprise en hellenia_prod | M3 |
| M5 | Import plan contable (ya en plantilla `do`) | M3 |
| M6 | Import categorías producto | M5 |
| M7 | Import proveedores | M6 |
| M8 | Import clientes | M6 |
| M9 | Import productos + existencias | M7,M8 |
| M10 | Rangos NCF DGII | M3 |
| M11 | Usuarios y permisos | M3 |
| M12 | Validación UAT repetida en PROD | M9,M10,M11 |
| M13 | Activar Traefik + URL | M12 |
| M14 | Corte usuarios a nueva URL | M13 |

---

## 3. Tiempo estimado (técnico)

| Escenario | Downtime comunicado | Trabajo técnico |
|-----------|---------------------|-----------------|
| Solo maestros (<500 productos) | 4–8 h | 6–10 h |
| Maestros + saldos iniciales | 8–12 h | 12–16 h |
| Migración histórica facturas | 24–48 h | Proyecto separado |

**Recomendación Fase 10:** Go-Live con maestros + saldos; histórico en fase posterior si requerido.

---

## 4. Puntos de control

| ID | Validación | Criterio éxito |
|----|------------|----------------|
| CP-01 | BD hellenia_prod creada | Login admin |
| CP-02 | Módulos Justech | 3 módulos installed |
| CP-03 | Empresa Hellenia | RNC 133621282 |
| CP-04 | Productos importados | Count = fuente Excel |
| CP-05 | Stock inicial | Cuadre inventario físico |
| CP-06 | NCF prueba | B01/B02 en rango real |
| CP-07 | UAT smoke en PROD | 10 checks PASS |
| CP-08 | URL HTTPS | LE válido |

---

## 5. Rollback

Ver [ROLLBACK_PLAN.md](ROLLBACK_PLAN.md). Punto de no retorno: comunicación URL + operación comercial en prod nueva.

---

## 6. Migración desde odoo-pecv (opcional)

| Dato | Método | Complejidad |
|------|--------|-------------|
| Partners | CSV export 18 → import 19 | Media |
| Productos | CSV + mapeo categorías | Media |
| Facturas históricas | **No recomendado** MVP — archivar PDF | Alta |
| Saldos contables | Asiento apertura manual | Requiere contador |

---

## 7. Estado Fase 10

**PASS CON OBSERVACIONES** — diseño completo; ejecución pendiente.

| Observación | Prioridad |
|-------------|-----------|
| Inventario de datos legacy odoo-pecv no extraído | P1 |
| Decisión histórico facturas pendiente Hellenia | P1 |
