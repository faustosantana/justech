# Firma real de laboratorio (NO DGII)

## Ubicación (solo servidor, fuera de Git)

`/opt/odoo-dev/secrets/ecf-lab/`

- `lab_valid.p12` — certificado válido de laboratorio
- `lab_expired.p12` — vencido
- `lab_corrupt.p12` — corrupto
- `lab_password.txt` — contraseña local
- `README` — marca NO cumplimiento DGII

## Dependencias (pin)

- `cryptography==41.0.7`
- `pyOpenSSL==23.3.0`
- `signxml==3.2.2`

## Resultado smoke 2026-07-12

- LAB_SIGN_VERIFY_TAMPER PASS
- CORRUPT_OK / BADPWD_OK
- DOC_SIGN verified; hash conservado
- NO envío DGII real

## Advertencia

Este material **NO** certifica cumplimiento DGII y **NO** debe usarse para envío real.
