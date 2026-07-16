#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Idempotent Helpdesk Enterprise config for justech_dev (odoo shell).

  sudo -u odoo odoo shell -c /opt/odoo-dev/conf/odoo-dev.conf -d justech_dev < apply_dev.py

No new models. No new cron. Reuses:
  - helpdesk.ir_cron_auto_close_ticket
  - helpdesk.rating_ticket_request_email_template
  - base.automation #15 (digest) and #14 (reopen)
"""
from pathlib import Path
from odoo import Command

DIGEST = Path(__file__).with_name('digest_server_action.py').read_text(encoding='utf-8')
OPERATIONAL_TEAM_IDS = {1, 2, 3, 4, 5}

Stage = env['helpdesk.stage']
Team = env['helpdesk.team']
cerrado = Stage.browse(8)
resuelto = Stage.browse(4)
cancelado = Stage.browse(5)
rating = env.ref('helpdesk.rating_ticket_request_email_template')

resuelto.write({'fold': False, 'sequence': 50, 'template_id': 82})
cerrado.write({'fold': True, 'sequence': 90, 'template_id': rating.id})
cancelado.write({'fold': True, 'sequence': 100})

for team in Team.with_context(active_test=False).search([]):
    if team.id not in OPERATIONAL_TEAM_IDS or not team.active:
        team.write({'use_rating': False, 'auto_close_ticket': False})
        continue
    vals = {
        'use_rating': True,
        'auto_close_ticket': True,
        'auto_close_day': 3 if team.company_id.id == 2 else 2,
        'to_stage_id': cerrado.id,
        'from_stage_ids': [Command.set([resuelto.id])],
    }
    if cerrado.id not in team.stage_ids.ids:
        vals['stage_ids'] = [Command.link(cerrado.id)]
    team.write(vals)

group = env.ref('helpdesk.group_use_rating')
for uid in env.ref('helpdesk.group_helpdesk_manager').user_ids.ids:
    env.cr.execute(
        "INSERT INTO res_groups_users_rel (gid, uid) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (group.id, uid),
    )
group.invalidate_recordset()

cron = env.ref('helpdesk.ir_cron_auto_close_ticket')
cron.active = True

env['ir.actions.server'].browse(1391).write({'state': 'code', 'code': DIGEST})
env['base.automation'].browse(15).write({
    'name': 'Recordatorio consolidado tickets pendientes',
    'active': True,
    'filter_domain': [('stage_id.fold', '=', False), ('team_id', 'in', [1, 2, 3, 4, 5]), ('active', '=', True)],
    'trg_date_range': 2,
    'trg_date_range_type': 'hour',
})

env.cr.commit()
print('HELPDESK_ENTERPRISE_CONFIG_APPLIED_IDEMPOTENT')
