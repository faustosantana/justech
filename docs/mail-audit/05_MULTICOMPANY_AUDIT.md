# 05 — Auditoría multiempresa

## Empresas `res.company` (IDs estables DEV=Prod)

| id | Nombre | Dominio esperado |
|---|---|---|
| 1 | JUSTECH S.R.L. | justech.do |
| 2 | PlugSafe SRL | plugsafeservices.com |
| 3 | Just Office SRL | just-offices.com |
| 4 | Omni Solutions SRL | solutionsomni.com |

## Contextos Odoo evaluados

| Mecanismo | ¿Causa del leak? | Evidencia |
|---|---|---|
| `ticket.company_id` incorrecto | **No** | mismatch ticket↔team = 0; repro ticket company_id=1 |
| `env.company` / `allowed_company_ids` | No como causa primaria | From viene del template/alias, no de env.company |
| `sudo()` en envío | No demostrado como root | política usa sudo solo en ICP |
| Logo / report layout | Puede **divergir** del From | layout sigue company del documento; From sigue alias → identidad mixta |
| Alias domain global `just-offices.com` | **Sí (config)** | teams 1,3,4,6 mal alineados |
| Política salida DEV 19.0.1.0.0 | **Sí (código/config)** | solo aplica a `justech.do`; no corrige From Just Office en ticket JUSTECH |
| Política worktree 19.0.1.1.0 | Mitigación parcial pendiente de deploy | selecciona por `record_company_id` / document company **antes** que dominio From |
| Templates hardcode JUSTECH | Fuga inversa multiempresa | ids 72/80/81/82 |
| Cache / OWL | No | problema server-side mail |
| ICP | `justech_mail.apply_domains=justech.do`, `force_from=notifications@justech.do` | single-tenant legacy en DEV |

## Matriz de fugas

| Escenario | From resultante (DEV policy 1.0.0) | Leak |
|---|---|---|
| JUSTECH team 5 | → notifications@justech.do | No |
| JUSTECH team 1 | customer-care@just-offices.com (sin rewrite) | **Just Office en JUSTECH** |
| PlugSafe team 4 | @just-offices.com | Just Office en PlugSafe |
| Omni team 3 | @just-offices.com | Just Office en Omni |
| Template 72 en Omni | asistencia@justech.do → policy puede forzar Justech | **JUSTECH en otras empresas** |

## Conclusión multiempresa

El sistema **sí** guarda `company_id` correcto en el ticket.  
La identidad visible del correo **no** está gobernada por `company_id`, sino por **alias del team** + **política de From** domain-based.
