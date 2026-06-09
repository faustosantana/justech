# LLM Router — JAIOS

## Endpoint

```
POST /api/v1/llm/completions
Authorization: Bearer <token>
X-Tenant-ID: <uuid>
```

```json
{
  "messages": [
    { "role": "user", "content": "Hola" }
  ],
  "provider": "openai",
  "model": "gpt-4o",
  "temperature": 0.7,
  "max_tokens": 1024
}
```

## Proveedores

| ID | Tipo | Config |
|----|------|--------|
| `openai` | Cloud | `OPENAI_API_KEY` |
| `claude` | Cloud | `ANTHROPIC_API_KEY` |
| `deepseek_huawei` | Cloud privado | `DEEPSEEK_HUAWEI_*` |
| `hermes_local` | Local (Ollama) | `HERMES_LOCAL_BASE_URL` |

## Resolución de proveedor

1. `provider` en request (override explícito)
2. `llm_provider_configs` del tenant (ordenado por `is_default`, `priority`)
3. `LLM_DEFAULT_PROVIDER` con fallback a `LLM_FALLBACK_PROVIDER`

## Extensión

Agregar proveedor en `backend/app/llm/providers/` e registrar en `PROVIDER_REGISTRY`.
