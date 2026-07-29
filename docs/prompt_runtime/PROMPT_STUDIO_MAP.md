# Prompt Studio Map

Autopsy for Prompt Runtime Integration 1.0. Paths relative to repo root.

## Answers (Fase 1)

1. **Where blocks are stored:** Postgres `jaios.lottery_ai_prompt_versions` (`blocks` JSONB, `body` Text, `checksum`). ORM `LotteryAiPromptVersion` in `backend/app/models/lottery.py`.
2. **Versions:** Multiple rows per `name`+`version` unique. Full version history via rows + `previous_version_id`.
3. **Draft / published / active:** Yes — statuses `draft` → `validated`/`approved` → `active` (publish replaces prior active → `replaced`). Drafts are editable; active is not edited in place (new draft from clone).
4. **“Ver compilado”:** Backend `GET /api/v1/lottery/admin/ai/prompts/{id}/compiled` using `compile_prompt_from_blocks`. Control Center page is read-only API consumer.
5. **Compile function:** `compile_prompt_from_blocks` in `backend/app/lottery/ai/prompt_studio.py`.
6. **Block order:** `identidad`, `dominio`, `memoria`, `aclaraciones`, `analisis`, `herramientas`, `respuesta`, `reglas_prediccion`, `instrucciones_especificas` (optional), `seguridad`.
7. **Cache:** In-process only (`set_analyst_from_db` / `clear_db_analyst_prompt` in V6; admin `_refresh_prompt_cache`). No Redis for prompts.
8. **Invalidation:** On publish / rollback / `ensure_seeded` refresh.
9. **Length limits:** Per-block max in `PROMPT_STUDIO_BLOCKS` validation (4k–8k). Soft UI warnings; draft update does not hard-fail on max.
10. **Who can publish:** Roles with `lottery_admin_prompts` / `lottery_admin_ai` / `lottery.admin` (owner/admin/superadmin). Publish also needs operational gates (optional `force`).
11. **History:** Version rows + `LotteryAiAuditEvent` (`prompt_create_draft`, `prompt_update_draft`, `prompt_publish`, `prompt_rollback`).
12. **Scope:** Lottery-module global catalog (`tenant_id` nullable; seeds global). Not multi-app.

## Critical gap

**Live Analyst Reasoning 2.1 does not call `compile_prompt_from_blocks`.** Chat Huawei system prompt is hardcoded in `build_reasoning_messages`. Prompt Studio edits admin UX + optional V6 cache path; Reasoning path is separate.

## Dual UIs

| UI | Path | Publish? |
|----|------|----------|
| Control Center | `/lottery/admin/control-center/prompt-studio*` | No (save draft + view compiled) |
| Legacy Admin | `/lottery/admin/ai/prompts` | Yes |

## Key files

| Role | Path |
|------|------|
| Schema/compile | `backend/app/lottery/ai/prompt_studio.py` |
| Service | `backend/app/services/lottery_ai_admin_service.py` |
| API | `backend/app/api/v1/lottery_ai_admin.py` |
| Model | `backend/app/models/lottery.py` (`LotteryAiPromptVersion`) |
| FE bloques | `frontend/src/app/(platform)/lottery/admin/control-center/prompt-studio/page.tsx` |
| FE compilado | `…/prompt-studio/compilado/page.tsx` |
| FE versiones | `…/prompt-studio/versiones/page.tsx` |
| Client | `frontend/src/lib/api.ts` (Prompt Studio helpers) |
