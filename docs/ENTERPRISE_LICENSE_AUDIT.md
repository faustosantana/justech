# Auditoría Licencia Enterprise

**Código suscripción:** `M260616306091776`  
**Fecha:** 2026-06-30  
**Referencia:** [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md)

---

## 1. Resumen bloque 3

| Control | Estado | Detalle |
|---------|--------|---------|
| Licencia Enterprise | PASS CON OBS | Código registrado en DEV |
| Código suscripción | PASS | M260616306091776 |
| Estado contrato | PASS CON OBS | Verificar "In Progress" en portal Odoo |
| Usuarios contratados | PASS CON OBS | Validar límite vs usuarios Go-Live |
| Renovación | PASS CON OBS | Monitorear fecha renovación |
| Activación PROD | PENDIENTE | Solo en `hellenia_prod` al Go-Live |
| Política 1 BD/código | PASS CON OBS | Crítico al Go-Live |

**Bloque 3:** PASS CON OBSERVACIONES

---

## 2. Estado actual por ambiente

| BD | Odoo | Licencia EE | Neutralizado |
|----|------|-------------|--------------|
| hellenia_dev | 19 EE | Registrado | No |
| hellenia_test | 19 EE | Heredado/neutralizado | Sí |
| odoo-pecv (legacy) | 18 | Posible vínculo legacy | No |
| hellenia_prod | — | No creada | — |

---

## 3. Política oficial Odoo

> *"Only one database can be linked per subscription."*

**Implicación Go-Live:**

1. Registrar `M260616306091776` en `hellenia_prod`
2. **Desvincular** BD anterior (odoo-pecv o DEV) antes o durante corte
3. DEV/TEST post-Go-Live: neutralizar o usar sin código activo

---

## 4. Riesgos

| ID | Riesgo | Impacto | Prioridad | Solución |
|----|--------|---------|-----------|----------|
| LIC-01 | Dos BDs con mismo código | Bloqueo registro | P0 | Desregistrar legacy pre-Go-Live |
| LIC-02 | Usuarios exceden contrato | Aviso Odoo 30d | P1 | Contar usuarios ROLE_MATRIX |
| LIC-03 | Sin conectividad services.odoo.com | Validación falla | P1 | Verificar firewall saliente :80 |

---

## 5. Checklist Go-Live licencia

| # | Paso |
|---|------|
| 1 | Confirmar contrato activo en odoo.com |
| 2 | Documentar BD vinculada actual |
| 3 | Desvincular BD no productiva |
| 4 | Registrar hellenia_prod |
| 5 | Verificar banner "valid subscription" |
| 6 | Neutralizar TEST si sigue en mismo código |

---

## 6. Estado Fase 10

**PASS CON OBSERVACIONES** — sin riesgo bloqueante de preparación; P0 al ejecutar Go-Live.
