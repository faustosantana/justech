# Resumen migración NCF Justech
- 14 rangos Justech activos desde legacy (safe_next = max publicado/legacy/justech + 1).
- JUSTECH B01: último B0100001614 → next B0100001615.
- Legacy preservado; Adel no genera números nuevos.
- Tests 1–7 PASS (rollback). FC/2026/00374 sin NCF (evidencia).
- Producción no modificada. Commit pendiente.
FC/2026/00374 no longer in DB (count 2403). Not modified in this closure; originally left without NCF as evidence.
