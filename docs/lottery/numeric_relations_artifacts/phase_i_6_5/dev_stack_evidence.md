# DEV stack evidence — I-6.5

## URLs
| Service | URL | Health |
|---------|-----|--------|
| Frontend (Control Center build) | http://127.0.0.1:3011 | HTTP 200 |
| API (official uvicorn entrypoint) | http://127.0.0.1:8001/api/v1 | /health ok |
| FE→API rewrite | /api/* → http://host.docker.internal:8001/api/* | proxy health 200 |
| Postgres DEV | 127.0.0.1:5433 / jaios_lottery_dev | up |
| Redis staging (shared) | 127.0.0.1:6380 | up |

## Git
- Branch: `feature/lottery-ia-control-center`
- Commit deployed to DEV stack: `e1ba664a7e5a6d8c680e82384fbec8d09f6205d5`
- Container FE: `jaios-cc-dev-web` (node:22-alpine + `npm run start` over built `.next`)
- Container API: `jaios-cc-dev-api` (`uvicorn app.main:app`)

## Database
- Name: `jaios_lottery_dev`
- Alembic: `061_lottery_ia_control_center`
- Draws count (historic unchanged check): `91927`
- Backup pre-061: `backups/jaios_lottery_dev_pre_061_20260724_084802.dump`

## Active prompt (must remain unchanged by drafts/playground)
```
ba2940bf-698f-4bea-8a39-31536f1bcc22
v2
lottery_assistant_system_v2
```

## Not used
- Slim server: no
- Production DB / deploy: not touched
- Sync write: not enabled/changed
