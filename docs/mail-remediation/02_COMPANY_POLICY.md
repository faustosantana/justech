# 02 — Company Policy (company-first)

## Flujo obligatorio

```
Documento.company_id
  → res.company._get_company_mail_identity()
  → force_from / domain / logo / layout / SMTP domain
  → mail.mail.send aplica From + Reply-To
  → ir.mail_server (from_filter por dominio del From)
  → Cliente
```

## Prohibido

- Usar `env.company` / empresa activa del usuario para identidad saliente
- Dejar que el dominio del alias determine la empresa
- Hardcodes de From en templates

## Helper

`res.company._get_company_mail_identity(reply_user=None)` devuelve:

- `email_from`, `reply_to`, `domain`, `display_name`
- `alias_domain_id`, `logo`, `layout_company`
- `smtp_domain`, `allowed_domains`, `policy`

## ICP

`justech_mail.company_policies` — JSON multiempresa (JUSTECH, Just Office, PlugSafe, Omni).  
`justech_mail.outgoing_policy_enabled` — kill switch.
