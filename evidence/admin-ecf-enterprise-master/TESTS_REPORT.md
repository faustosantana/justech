# Tests — resumen

## Shell integration (2026-07-12)

```
PASS sign_verify
PASS tamper
PASS api_inbound
PASS engines
PASS operations
SUMMARY ALL_PASS
```

## Smoke previo

- LAB_SIGN_VERIFY_TAMPER PASS
- CORRUPT_OK / BADPWD_OK
- RECEIVE + DUP + ACK
- API health / documents / receive / 401
- BENCH 100 / 1k / 10k (ver PERFORMANCE_REPORT.md)
- UNBALANCED 0
- AUTH hash intacto

## Nota CLI Odoo 19

`odoo --test-enable` sin subcomando `server` no ejecuta tests en esta instalación.  
Suite unitaria presente en módulos; validación ejecutada vía smoke + shell integration en `justech_dev`.
