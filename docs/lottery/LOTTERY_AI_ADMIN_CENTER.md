# Centro de Administración de Lottery IA

**Ruta:** `/lottery/admin/ai`  
**Permisos:** `lottery_admin_ai`, `lottery_admin_prompts`, `lottery_admin_models`, `lottery_admin_tools`, `lottery_admin_safety` (también `lottery.admin` / owner / admin).  
**Clientes Lottery:** 403 / menú oculto.

## Qué controla
- Dashboard runtime (Huawei, Hermes honesto: no orquestador)
- Prompt Studio (borrador → publicar → rollback; activo en DB)
- Modelos (sin secretos)
- Agente / memoria / tools / packs / loterías predeterminadas
- Seguridad + tests permanentes (incl. «esas loterías»)
- Playground sandbox
- Benchmarks / versiones / auditoría

## Persistencia
Migración `059_lottery_ai_admin_center`.  
Prompt activo: `lottery_ai_prompt_versions` con cache de proceso; fallback al registro en código.

## No tocado
Sync (3 loterías), Nacional Día, Etapa C, Hermes orquestador.
