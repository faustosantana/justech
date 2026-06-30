# Plan de Soporte Post Go-Live

**Cliente:** Hellenia, S.R.L.  
**Proveedor técnico:** Justech  
**Versión:** 1.0 Fase 10

---

## 1. Bloque 10 — Resumen

| Periodo | Enfoque | Estado diseño |
|---------|---------|---------------|
| Primer día | War room, smoke, incidencias P0 | PASS |
| Primera semana | Estabilización, formación usuarios | PASS |
| Primer mes | Optimización, backlog menor | PASS |

**Bloque 10:** PASS

---

## 2. Primer día (D+0)

| Hora | Actividad | Responsable |
|------|-----------|-------------|
| H+0 | Monitoreo activo logs Odoo/Traefik/PostgreSQL | Justech IT |
| H+1 | Confirmar backups automáticos ejecutados | Justech IT |
| H+2 | Revisión incidencias usuarios | Hellenia + Justech |
| H+4 | Checkpoint gerencia — go/no-go continuidad | Hellenia |
| H+8 | Informe cierre día 1 | Justech |

**Canal incidencias:** `it@justech.do` + grupo acordado con Hellenia

---

## 3. Primera semana (D+1 a D+7)

| Día | Actividad |
|-----|-----------|
| D+1 | Revisión CxC/CxP y primeras facturas NCF reales |
| D+2 | Soporte usuarios por rol (Ventas, Compras, Contabilidad) |
| D+3 | Validación reportes 606/607 con contador |
| D+4 | Ajustes parametrización menor (sin código) |
| D+5 | Retrospectiva semana 1 |

---

## 4. Primer mes (D+8 a D+30)

- Revisión performance (workers, RAM)
- Carga catálogo remanente si faseada
- Configuración monitoreo/alertas
- Plan actualización parches Odoo (ventana mensual)

---

## 5. SLA propuesto

| Prioridad | Descripción | Tiempo respuesta | Tiempo resolución |
|-----------|-------------|------------------|-------------------|
| P0 | Sistema caído / fiscal bloqueado | 1 h | 4 h |
| P1 | Función crítica degradada | 4 h | 24 h |
| P2 | Defecto no bloqueante | 1 día hábil | 5 días hábiles |
| P3 | Mejora / consulta | 3 días hábiles | Planificado |

*Horario hábil: Lun–Vie 8:00–18:00 AST*

---

## 6. Ventanas de mantenimiento

| Tipo | Frecuencia | Duración |
|------|------------|----------|
| Parche seguridad | Según CVE | 2–4 h, notificar 48h |
| Upgrade Odoo minor | Mensual evaluación | 4–8 h, notificar 1 semana |
| Backup restore drill | Trimestral | 2 h |

---

## 7. Escalación

| Nivel | Contacto |
|-------|----------|
| L1 | Usuario → supervisor Hellenia |
| L2 | Justech IT (`it@justech.do`) |
| L3 | Justech arquitecto / contador fiscal |
| L4 | Odoo Enterprise support (si aplica contrato) |

---

## 8. Estado Fase 10

**PASS** — plan operativo diseñado; activar al Go-Live.
