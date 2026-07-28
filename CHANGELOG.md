# Changelog

## [Unreleased]

## [2026.1] — Lottery Analyst CERTIFIED — 2026-07-28

### lottery-ia-ux-v2.4.5.4-certified (FROZEN)

- **Status:** CERTIFIED — 200 PASS / 0 FAIL (`cert200-20260728T151731Z-40ca7b78`).
- **Baseline:** `LOTTERY_ANALYST_CERTIFIED_2026_1` frozen at tag `lottery-ia-ux-v2.4.5.4-certified`.
- **Commit:** `8061e0f458419d994bff8abd3700de4c10aa5b80`.
- **Docker:** `jaios-app-backend:lottery-ia-ux-v2.4.5.4-de` (`sha256:a6204913747cc2472f2dfec4cd125b95f73fe1fd55439d6d1255c9342780af24`); aliases `lottery-ia-ux-v2.4.5.4`, `lottery-analyst-certified-2026.1`.
- **Bank / seed:** SHA-256 `6d056978809140eee4af23299cbd0c78a8bae9537fbbbcd62ad50bd18c6d7931`, seed `20260727` (locked).
- Closed blocked baseline (175/25) via conversational root causes A–E only; Prompt Maestro / Hermes / mathematical motor unchanged.
- Release pack: `RELEASE_PACKAGE/` (`RELEASE_NOTES_2026.1.md`, `CERTIFICATION_REPORT_FINAL.md`, `VERSION_MANIFEST.json`, `RESTORE.md`, `verify_restore.sh`).
- Evidence: `evidence/lottery-analyst-certification-200/audit-certified-20260728/`.

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
