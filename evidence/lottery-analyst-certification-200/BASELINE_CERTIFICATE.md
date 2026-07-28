# BASELINE CERTIFICATE — LOTTERY_ANALYST_CERTIFIED_2026_1

**Status:** FROZEN  
**UTC:** 2026-07-28T03:16:00Z  

## Identity

| Field | Value |
|-------|-------|
| Baseline name | `LOTTERY_ANALYST_CERTIFIED_2026_1` |
| Version tag | `lottery-ia-ux-v2.4.5.3` |
| Certified tag | `lottery-analyst-certified-2026.1` |
| Commit | `ec27d96ecba3267a9879861b6355cbe642f2f41e` |
| Environment | production `jaios.justech.do` |

## Runtime

| Service | State |
|---------|-------|
| Backend image | `jaios-app-backend:lottery-ia-ux-v2.4.5.3` |
| Backend digest/id | `sha256:68f2db99229a81359706298c5792fba72aa2d7dce7e6ab23ac276b4353468ce8` |
| Frontend | `jaios-app-frontend:lottery-ia-ux-v2.4.5.3` |
| Postgres | healthy |
| Redis | PONG |
| Hermes | healthy (HTTP 200) |
| Gateway | up |

## Schema / data

| Field | Value |
|-------|-------|
| Alembic | `061_lottery_ia_control_center` |
| DB backup | `/var/jaios/backups/LOTTERY_ANALYST_CERTIFIED_2026_1_20260728_031519.dump` |
| Backup SHA-256 | `94fcc63befcba347d843563cab54e377fc2404230e86fcf4abb4ed459d4182c3` |

## Integrity

- Prompt Maestro v5 file present and checksummed.
- `LOTTERY_ANALYST_SYSTEM_V6` active (`DeepSeek-V3.2`).
- Motor: `35+14 → 54`, `39+58 → 94`.
- Ranking / tables / motor freeze artifact unchanged by this freeze.
- Prior conversational audit: **44 PASS / 0 FAIL**, jerga **0**.

## Pre-freeze regressions

All mandatory conversational + motor checks **PASS** (last 22, last3 97, Nacional inherit, last 44, correction 97, same_day 55+24, compare 54/94).

## Rollback

1. Redeploy image tag `lottery-ia-ux-v2.4.5.3` / git tag `lottery-analyst-certified-2026.1`.
2. If data damaged: `pg_restore` from the backup path above.
3. Do not move this certified tag; create a new tag for any later baseline.

## Evidence

- `FREEZE_MANIFEST.json`
- `freeze/critical_checksums.json`
- `freeze/freeze_precheck.json`
- `freeze/freeze_chat_regressions.json`
- Server: `/var/jaios/lottery-certification/2026.1/`
