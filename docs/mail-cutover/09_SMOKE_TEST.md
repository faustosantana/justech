# 09 — Smoke Test (preparado, no ejecutado)

Tras un futuro cutover autorizado, en Prod:

## Por empresa (JUSTECH, Just Office, PlugSafe, Omni)

1. Ticket Helpdesk en team de esa company → From dominio correcto  
2. Cotización sale.order → From dominio correcto  
3. (Opcional) factura / RFQ / CRM message  

## Checks globales

- Alias mismatches = 0  
- Templates 72/80/81/82 sin `asistencia@justech.do` literal  
- `env.company` trap: documento JUSTECH con UI en Just Office → From justech.do  
- Logs sin SendAsDenied / connection refused  

## DEV reference

UAT maestro PASS: `docs/mail-uat/`
