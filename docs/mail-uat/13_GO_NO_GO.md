# 13 — GO / NO-GO

## Checklist

| Criterio | Estado |
|---|---|
| Restore PASS | ✓ |
| Hardcodes corporativos = 0 | ✓ |
| Alias cruzados = 0 | ✓ |
| Correos cruzados = 0 | ✓ |
| SMTP cruzados = 0 | ✓ |
| Logos cruzados = 0 | ✓ (layout company = document company en helper) |
| Reply-To cruzados = 0 | ✓ (no force_from ajeno; humano permitido) |
| Company Policy siempre | ✓ |
| 4 empresas × módulos | ✓ |
| Sin regresiones | ✓ |
| Literal IAP `iap@odoo.com` | Documentado (1) |
| Producción desplegada | **NO** |

## Decisión

**GO PARA PRODUCCIÓN: NO**

Justificación: UAT DEV de identidad corporativa multiempresa está **PASS**, pero:

1. Producción no debe desplegarse sin autorización expresa.
2. Existe un literal From residual de Odoo IAP (`iap@odoo.com`) documentado; no afecta cruce Justgroup, pero debe decidirse antes/durante el release plan.
3. En Prod el SMTP real (from_filter) debe validarse en un cutover controlado aparte del UAT DEV (sink Neutralization).
