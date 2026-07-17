# 15 — Plan de remediación (NO EJECUTAR)

## Principios

- Autorización expresa por paquete.
- Backup + UAT DEV + (si aplica) UAT Prod.
- Separar: funcional / fiscal / datos / UX / refactor / features.
- **Baseline NCF alerts fuera de alcance** salvo incidencia.

## P0 — Críticos

### Paquete P0.1 — Fuente de verdad NCF
- **Alcance:** definir canónico LATAM vs Justech; sincronización FDP; política de lectura reportes
- **Módulos:** base, ncf, reports
- **Riesgos:** migración datos; reportes
- **Pruebas:** unicidad v2, FDP, 606/607 smoke
- **Empresas:** 4
- **Estimación:** L
- **GO:** inventario campos + matriz decisión firmada

## P1 — Altos

### P1.1 — Bloqueo/corrección prefijo≠tipo
- Datos históricos vs gate publicación
- Relacionado fix compras recibido ya en Prod (no reabrir sin necesidad)

### P1.2 — Población roles fiscales (SoD)
- Asignar Responsable/Usuario por empresa; no tocar baseline alert logic

### P1.3 — Cron Adel expire sequences
- Análisis impacto; posible freeze/flag (adel_freeze ya existe)

### P1.4 — Revisar commits padrón
- Sustituir commits por savepoints/batches seguros

## P2 — Medios

- Hardening except/sudo/limit=1 con pruebas
- Evidencia E2E 608/609
- Decidir hellenia_account
- Normalizar NCF case

## P3 — Bajos / limpieza / UX / docs

- Etiquetas, menús, documentación usuario
- Inventario continuo

## Cobertura de pruebas (paquete transversal)

- Tests prefijo≠tipo LATAM+Justech
- Matriz ACL roles
- Smoke 606–623 multiempresa SAVEPOINT

## Orden recomendado

1. P0.1 decisión arquitectura  
2. P1.1 gate prefijo  
3. P1.2 roles  
4. P1.3 Adel cron  
5. P1.4 padrón commits  
6. P2…  

## Criterios GO/NO-GO globales

- GO solo con backup DEV + restore PASS + UAT SAVEPOINT  
- NO-GO si toca baseline alertas o Prod sin plan  
- NO mezclar refactor con fix fiscal en el mismo PR
