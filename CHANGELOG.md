# Changelog

## [Unreleased]

### Lottery IA — Fase 5.2 (2026-07-26)

- **Dashboard Lottery IA** (`/lottery/ia`): tarjetas de Motor, Resultados, Piloto, Rendimiento y Último sorteo. API de solo lectura `GET /lottery/ia/dashboard` y `GET /lottery/ia/motor-freeze`.
- **Motor v1.0 congelado** (registro de producto): versión 1.0, perfil `socio`, tiebreak operativo multi-fuerte, fecha 2026-07-26, commit actual. No editable desde la UI.
- **UX Tabla 1 / Tabla 2**: se eliminan columnas Número y Cantidad de la grilla; se mantienen buscadores; orden por Código; sin paginación (hasta 100 filas en una página).
- Documentación: `docs/lottery/dashboard/FASE_5_2_DASHBOARD.md`.
- Sin cambios en Motor, Ranking, Tiebreak, J-11A ni Producción.

### Lottery — Fase 5.1

- Centro de Resultados sobre sorteos oficiales (`/lottery/resultados`), reutilizando sync/adapters existentes.

### Lottery — Fase 4

- Persistencia del piloto prospectivo DEV/UAT.

### Lottery — Fase 3

- Tiebreak multi-fuerte y validación prospectiva (lab).
