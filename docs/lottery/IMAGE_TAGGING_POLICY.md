# Image Tagging Policy — JAIOS Lottery / Backend

## Canonical deploy tag

**`latest`** is the single tag Compose uses for production deploy of:

- `jaios-app-backend:latest`
- `jaios-app-frontend:latest`

Do not deploy from `bid-live-uat` or other experimental tags unless explicitly authorized.

## Immutable release tags

For this consolidation:

| Image | Tag | Role |
|-------|-----|------|
| `jaios-app-backend` | `lottery-official-20260722` | Release bake (immutable pointer) |
| `jaios-app-frontend` | `lottery-official-20260722` | Release bake |
| `jaios-app-backend` | `pre-lottery-official-20260722` | Rollback base (pre-bake `latest`) |
| `jaios-app-frontend` | `pre-lottery-official-20260722` | Rollback FE |
| `jaios-app-backend` | `lottery-hotpatch-snapshot-20260722` | Forensic only (pre-bake running container) |
| `jaios-app-backend` | `bid-live-uat` | **Non-canonical** — Bid Center experiment; do not use for Lottery prod |

## Rules

1. Production Compose always tracks **`latest`**.
2. Before changing `latest`, tag the current `latest` as `pre-<change>-YYYYMMDD`.
3. After a successful bake/deploy, also tag `latest` as `<feature>-official-YYYYMMDD`.
4. Keep rollback tags until the next authorized cleanup.
5. Never delete `pre-*` or `*-official-*` tags until rollback window closes.
