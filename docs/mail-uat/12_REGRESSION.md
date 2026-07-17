# 12 — Regresión

| Módulo | Estado |
|---|---|
| helpdesk | installed |
| crm | installed |
| sale | installed |
| purchase | installed |
| account | installed |
| portal | installed |
| mail | installed |
| auth_signup | installed |

Flujos UAT (create + mail policy) PASS sin excepciones en errores ORM.

SMTP DEV: solo Neutralization `localhost:1025` activo — sin envío externo.

mail.thread / mail.mail / mail.notification: ejercidos vía message_post + mail.mail.create + policy.

**Regresión funcional: PASS**
