# 06 — Causa raíz

## Veredicto

**Causa raíz primaria: configuración incorrecta de `mail.alias` / `alias_domain` en `helpdesk.team` de JUSTECH (y otros), combinada con plantillas que usan `team.alias_email_from` y una política de salida en DEV que no reescribe From de dominios ajenos.**

No es un bug de `company_id` en el ticket.  
No es OWL.  
No es cache.  
SMTP amplifica en Prod pero no origina el From.

## Cadena causal (demostrada)

### 1) Configuración — alias

`helpdesk.team` id=1 (company JUSTECH):

- `alias_name` = `customer-care`
- `alias_domain` = **`just-offices.com`**
- Esperado para JUSTECH: dominio **`justech.do`**

Evidencia: `evidence/mail-audit/SQL/03_aliases_helpdesk.txt`

### 2) Código Enterprise / plantilla — emite From del alias

`mail.template` id=73:

```text
{{ (object.team_id.alias_email_from or object.company_id.email_formatted or ...) }}
```

Reproducción SAVEPOINT (rollback):

```json
"repro_ticket": {
  "company_id": 1,
  "team_id": 1,
  "template73_rendered_from": "\"OdooBot\" <customer-care@just-offices.com>"
}
```

Evidencia: `evidence/mail-audit/repro/09_repro_results.json`

### 3) Código custom DEV — no corrige

Archivo DEV:  
`/opt/odoo-dev/custom-addons/justgroup/custom_addons/justech_mail_outgoing_policy/models/mail_mail.py`  
Versión: **19.0.1.0.0**

Método: `_justech_policy_applies`

```python
domain = original_addr.rsplit("@", 1)[-1]
if domain in domains:  # domains = {justech.do}
    return True
# ... user domain in justech.do ...
return False  # ← From @just-offices.com → False → From intacto
```

Resultado: cliente recibe identidad Just Office en ticket JUSTECH.

Copia evidencia: `evidence/mail-audit/codigo/07_mail_mail_policy_dev.py.txt`

### 4) Consecuencia secundaria

- Logo/layout puede seguir `ticket.company_id=JUSTECH` mientras From es Just Office → **identidad mixta**.
- En Prod, `ir.mail_server` con `from_filter` Just Office enviaría ese correo por SMTP Just Office.

### 5) Causas secundarias (checklist)

| Hipótesis | Resultado |
|---|---|
| company_id incorrecto en ticket | DESCARTADA (0 mismatches; repro company_id=1) |
| sudo() cambia company | No demostrado como root |
| company_id heredado / env.company | No decide From del template |
| template global sin company | Templates usan team alias / hardcode |
| SMTP global | DEV sink; Prod amplificador |
| alias global just-offices.com | **CONFIRMADA** |
| logo global | Layout por company documento (divergencia) |
| overrides Justech helpdesk | No hay `justech_helpdesk` |
| cron / automations | No necesario para explicar From |
| hardcode templates 72/80/81/82 | **CONFIRMADA** (fuga inversa) |
| company_id=False / =1 fijo | No en repro |
| self.env.company indebido en policy 1.0.0 | Policy domain-based, no company-first |
| policy 1.1.0 no desplegada en DEV | **CONFIRMADA** (gap) |

## Clasificación FASE 8

| Tipo | ¿Aplica? |
|---|---|
| Configuración | **SÍ — primario** |
| Código (política incompleta) | **SÍ — amplificador / falta de guardrail** |
| Template | **SÍ — vector** (`alias_email_from` + hardcodes) |
| SMTP | Amplificador Prod |
| Helpdesk | Datos de team/alias |
| Mail.thread | Conducto, no root |
| Multiempresa | Diseño alias no alineado a company |
| Contexto / herencia / cache / OWL | No |

## Responsables formales

| Campo | Valor |
|---|---|
| Componente | `helpdesk.team` alias domain + `justech_mail_outgoing_policy` (DEV 1.0.0) |
| Método | emisión: `alias_email_from` vía template; no-corrección: `_justech_policy_applies` |
| Archivo | DEV `justech_mail_outgoing_policy/models/mail_mail.py`; datos `mail_alias` / `mail_alias_domain` |
| Empresa afectada (síntoma reportado) | JUSTECH (puede mostrar Just Office) |
| También afectados | Omni, PlugSafe (aliases en just-offices.com) |
