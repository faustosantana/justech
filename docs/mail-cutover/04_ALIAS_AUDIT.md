# 04 — Alias / Helpdesk Audit (PROD)

Fuente: `evidence/mail-cutover/prod/06_helpdesk_aliases.txt`  
**Mismatch count: 4**

| team | company | alias | alias_domain | company_domain | alignment |
|---|---|---|---|---|---|
| 1 Atención al cliente | JUSTECH | customer-care | **just-offices.com** | justech.do | **MISMATCH** |
| 2 Atención al cliente | Just Office | atencion-al-cliente-justoffice-srl | just-offices.com | just-offices.com | OK |
| 3 Atención al cliente | Omni | …omni… | **just-offices.com** | solutionsomni.com | **MISMATCH** |
| 4 Atención al cliente | PlugSafe | …plugsafe… | **just-offices.com** | plugsafeservices.com | **MISMATCH** |
| 5 Soporte Justech | JUSTECH | asistencia | justech.do | justech.do | OK |
| 6 Cotizaciones / Ventas | JUSTECH | (vacío) | **just-offices.com** | justech.do | **MISMATCH** |

## DEV

Todos **OK** (0 mismatches) tras remediación P1.

## Duplicados / huérfanos

Ver `10_dup_aliases.txt` en evidencia Prod (inventario; no modificado).
