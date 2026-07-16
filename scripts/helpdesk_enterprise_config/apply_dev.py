#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply Helpdesk Enterprise professional config on justech_dev (odoo shell).

Usage (DEV only):
  sudo -u odoo /usr/bin/odoo shell -c /opt/odoo-dev/conf/odoo-dev.conf -d justech_dev < apply_dev.py

No new models. No new cron. Reuses helpdesk.ir_cron_auto_close_ticket and
helpdesk.rating_ticket_request_email_template.
"""
from pathlib import Path
from odoo import Command

DIGEST_PATH = Path(__file__).with_name('digest_server_action.py')
DIGEST_CODE = DIGEST_PATH.read_text(encoding='utf-8')

Stage = env['helpdesk.stage']
Team = env['helpdesk.team']
cerrado = Stage.browse(8)
resuelto = Stage.browse(4)
cancelado = Stage.browse(5)
rating_tmpl = env.ref('helpdesk.rating_ticket_request_email_template')

# Stages
resuelto.write({'fold': False, 'sequence': 50, 'template_id': 82})
cerrado.write({'fold': True, 'sequence': 90, 'template_id': rating_tmpl.id})
cancelado.write({'fold': True, 'sequence': 100})

for team in Team.search([]):
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

cron = env.ref('helpdesk.ir_cron_auto_close_ticket')
cron.active = True

act = env['ir.actions.server'].browse(1391)
act.write({'state': 'code', 'code': DIGEST_CODE})
auto = env['base.automation'].browse(15)
auto.write({
    'name': 'Recordatorio consolidado tickets pendientes',
    'active': True,
    'filter_domain': [('stage_id', 'in', [1])],
})

env.cr.commit()
print('HELPDESK_ENTERPRISE_CONFIG_APPLIED')
print('rating_tmpl', rating_tmpl.id, 'cron', cron.active, 'teams', Team.search_count([]))
