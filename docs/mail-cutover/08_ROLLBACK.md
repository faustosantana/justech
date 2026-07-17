# 08 — Rollback (documentado, no ejecutado)

## Triggers

- From cruzado post-deploy
- SMTP failures masivos
- Helpdesk/CRM/Sales mail regression
- Upgrade falla

## Procedimiento

1. Stop odoo  
2. Restaurar módulo desde backup filesystem  
3. Restaurar DB dump pre-cutover  
4. Restaurar filestore si hubo cambios binarios  
5. Start odoo  
6. Smoke mínimo: 1 correo JUSTECH + 1 Just Office  

## Kill switch parcial (si código nuevo ya cargado)

ICP `justech_mail.outgoing_policy_enabled=False` — **solo** desactiva rewrite; **no** revierte aliases/templates. Preferir restore completo si datos ya migraron.
