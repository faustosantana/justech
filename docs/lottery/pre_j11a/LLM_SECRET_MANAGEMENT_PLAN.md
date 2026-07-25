# LLM Secret Management Plan (Pre-J11A / TD-010)

## Threat model

| Amenaza | Mitigación |
|---------|------------|
| API key en texto plano en BD | Cifrado Fernet en reposo |
| Clave maestra en BD | `JAIOS_CREDENTIAL_ENCRYPTION_KEY` solo en env/secret store del host |
| Exposición en frontend | Respuestas solo `api_key_masked`; reveal solo runtime backend |
| Exposición en logs | `redact_for_logs`; audit sin plaintext |
| Uso cruzado DEV/PROD | Campo `environment` obligatorio; reveal falla si no coincide |
| Rotación sin rastro | Eventos `llm_secret.created` / `.rotated` / `.runtime_reveal` |

## Diseño

```
Admin (permiso AI) → store_secret / rotate_secret
                         ↓
              credential_vault.encrypt_secret
                         ↓
              ciphertext (memoria ahora; tabla DB en J-11A)
                         ↓
              public_view → masked only
                         ↓
Runtime Agent (futuro) → reveal_for_runtime(env)
```

## Implementación actual (fundación)

| Pieza | Ubicación |
|-------|-----------|
| Vault Fernet | `backend/app/services/credential_vault.py` |
| Store LLM | `backend/app/lottery/llm_secret_store.py` |
| Tests | `backend/tests/test_pre_j11a_llm_secrets.py` |

**No** se conectan proveedores reales en esta fase.  
**No** hay API keys reales en fixtures/docs.

## Cifrado

- Algoritmo: Fernet (AES-128-CBC + HMAC)
- Material: `JAIOS_CREDENTIAL_ENCRYPTION_KEY` (preferido) o derivado SHA-256 de `app_secret_key` (legacy)
- Clave maestra **fuera** de la base de datos

## Rotación

1. `rotate_secret(id, plaintext_new, actor)`
2. Sobrescribe ciphertext; actualiza `rotated_at` / `rotated_by`
3. Auditoría sin valor

## Masking

`abcd…wxyz` (4+4) vía `mask_secret`.

## Permisos (J-11A)

- Solo roles admin AI / `lottery.admin`
- Reveal runtime: proceso de backend, nunca endpoint público

## Recuperación / backup / restore

- Backup de ciphertext OK; inutilizable sin clave maestra
- Rotar clave maestra = re-cifrar todos los secretos (runbook J-11A)
- Incident response: revocar keys en proveedor + rotate + auditar `runtime_reveal`

## Proveedores futuros

`huawei_modelarts` | `openai` | `compatible` — abstracción lista; wiring en J-11A.

## Logging

Solo metadatos (`secret_id`, `provider`, `environment`, `actor`). Nunca plaintext.
