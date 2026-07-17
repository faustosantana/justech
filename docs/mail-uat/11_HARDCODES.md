# 11 — Hardcodes

## Corporativos (Justgroup) — gate UAT

**Hardcodes corporativos restantes: 0**

No hay `email_from` literal con:
- `@justech.do` / `@just-offices.com` / `@plugsafeservices.com` / `@solutionsomni.com`
- `asistencia@` / `customer-care@` fijos en templates Helpdesk (corregidos en P1)

Alias cruzados: **0**

## Literal From residual (fuera de identidad Justgroup)

| ID | Modelo | Nombre | email_from | Clasificación |
|---|---|---|---|---|
| 45 | iap.account | Notificación de generación de leads IAP | `iap@odoo.com` | Odoo IAP core — no cruza empresas Justgroup |

**No se corrigió silenciosamente** (instrucción UAT). Documentado para decisión de producto.

Gate estricto `literal_from==0` del script ORM = FAIL solo por este IAP → `go=false` en JSON crudo.  
Gate corporativo multiempresa = **PASS**.
