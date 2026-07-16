
tickets = env['helpdesk.ticket'].search([
    ('stage_id', 'in', [1]),
    ('active', '=', True),
], order='id asc')
if not tickets:
    log('Sin tickets pendientes')
else:
    lead = tickets[0]
    if records and records[0].id != lead.id:
        log('Skip digest duplicate trigger for ticket %s' % records[0].id)
    else:
        now = datetime.datetime.utcnow()
        rows = []
        for t in tickets:
            horas = 0
            if t.create_date:
                horas = int((now - t.create_date).total_seconds() // 3600)
            last = t.write_date.strftime('%Y-%m-%d %H:%M') if t.write_date else ''
            rows.append(
                "<tr>"
                "<td>%s</td>"
                "<td>%s</td>"
                "<td>%s</td>"
                "<td>%s</td>"
                "<td>%s</td>"
                "<td>%s</td>"
                "<td>%s</td>"
                "<td>%s</td>"
                "</tr>" % (
                    t.display_name or t.name or t.id,
                    (t.partner_id.name or ''),
                    (t.company_id.name or ''),
                    (t.stage_id.name or ''),
                    dict(t._fields['priority'].selection).get(t.priority, t.priority or ''),
                    (t.user_id.name or 'Sin asignar'),
                    last,
                    horas,
                )
            )
        base = env['ir.config_parameter'].sudo().get_param('web.base.url')
        helpdesk_url = '%s/odoo/helpdesk' % base.rstrip('/')
        body = (
            "<div style='font-family:Arial,sans-serif;font-size:14px;color:#111827;'>"
            "<p>Hay <strong>%s</strong> tickets pendientes en estado <strong>Nuevo</strong>.</p>"
            "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;width:100%%;max-width:960px;'>"
            "<thead style='background:#f3f4f6;'>"
            "<tr>"
            "<th>Número</th><th>Cliente</th><th>Empresa</th><th>Estado</th>"
            "<th>Prioridad</th><th>Asignado</th><th>Última actividad</th><th>Horas abiertas</th>"
            "</tr></thead><tbody>%s</tbody></table>"
            "<p><a href='%s' style='display:inline-block;padding:10px 16px;background:#111827;color:#fff;text-decoration:none;border-radius:4px;'>Abrir Helpdesk</a></p>"
            "<p style='color:#6b7280;font-size:12px;'>Recordatorio consolidado para el equipo Helpdesk.</p>"
            "</div>"
        ) % (len(tickets), "".join(rows), helpdesk_url)
        group = env.ref('helpdesk.group_helpdesk_manager')
        partners = group.user_ids.mapped('partner_id').filtered(lambda p: p.email)
        if not partners:
            group = env.ref('helpdesk.group_helpdesk_user')
            partners = group.user_ids.mapped('partner_id').filtered(lambda p: p.email)
        if partners:
            env['mail.mail'].sudo().create({
                'subject': 'Recordatorio Helpdesk: %s tickets pendientes' % len(tickets),
                'body_html': body,
                'email_to': ','.join(sorted(set(partners.mapped('email')))),
                'auto_delete': False,
            })
            log('Digest encolado a %s partners (%s tickets)' % (len(partners), len(tickets)))
        else:
            log('Sin destinatarios en grupos Helpdesk')

