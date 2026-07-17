# P0.1 — Sincronización FDP

## Qué es FDP hoy

`justech.do.fiscal.data.provider` — **solo lectura**.  
No escribe campos. No consume secuencias.

## Prioridad de lectura NCF

1. `justech_do_ncf`
2. `l10n_latam_document_number`
3. campos estándar con forma NCF (`ref` / `payment_reference` / `name`)

## Dirección de sync (compat_sync)

| Antes P0.1 | Después P0.1 |
|---|---|
| Justech → LATAM si `ncf_dual_write` ON (default ON) | Justech → LATAM **deshabilitado** |
| LATAM → Justech | No existe (correcto) |

## Momentos

- Assignment `assignment_write_vals` / `sync_manual_ncf` — respetan flag.
- Import padrón / API: no sincronizan NCF vía FDP.
- Reportes: solo `get_*`.

## Diseño post-P0.1

- Idempotente: re-leer FDP siempre.
- Sin recursion: no se escribe `justech_do_ncf` desde mirror.
- Sin sudo extra en FDP.
- Divergencia en **nuevos** docs: bloqueo al publicar (gate prefijo).
- Divergencia **histórica**: inventariada, no autocorregida.
