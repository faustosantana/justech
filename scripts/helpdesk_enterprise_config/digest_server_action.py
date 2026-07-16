
# Recordatorio agrupado Helpdesk — un correo por empresa (sin cruzar datos).
# Disparado por automation #15; solo el ticket "lead" de cada empresa envía.

AUTHORIZED_TEAM_IDS = [1, 2, 3, 4, 5]  # Atención al cliente + Soporte Justech (no Cotizaciones)
STAGE_NUEVO = 1
STAGE_EN_PROCESO = 2
STAGE_EN_ESPERA = 3
STAGE_ESPERANDO_CLIENTE = 6
STAGE_RESUELTO = 4

Ticket = env['helpdesk.ticket']
base_domain = [
    ('active', '=', True),
    ('stage_id.fold', '=', False),
    ('team_id', 'in', AUTHORIZED_TEAM_IDS),
]
pending = Ticket.search(base_domain, order='company_id, id asc')
if not pending:
    log('Sin tickets pendientes de seguimiento')
else:
    # Solo el lead global evita ráfagas; el envío real es por empresa.
    companies = pending.mapped('company_id')
    trigger = records[:1] if records else pending[:1]
    trigger_company = trigger.company_id
    company_tickets = pending.filtered(lambda t: t.company_id == trigger_company)
    if not company_tickets:
        log('Skip: sin tickets para empresa del trigger')
    else:
        lead = company_tickets.sorted(lambda t: t.id)[0]
        if trigger.id != lead.id:
            log('Skip digest duplicate for ticket %s company %s' % (trigger.id, trigger_company.id))
        else:
            now = datetime.datetime.utcnow()
            soon = now + datetime.timedelta(hours=24)

            def bucket(t):
                sid = t.stage_id.id
                if sid == STAGE_ESPERANDO_CLIENTE:
                    return 'waiting_client'
                if sid == STAGE_RESUELTO:
                    return 'resolved_pending'
                if sid in (STAGE_NUEVO, STAGE_EN_ESPERA) or (sid == STAGE_EN_PROCESO and not t.user_id):
                    return 'no_tech_reply'
                if sid == STAGE_EN_PROCESO:
                    return 'no_tech_reply'
                return 'other'

            def sla_label(t):
                if t.sla_fail:
                    return 'Vencido'
                if t.sla_deadline and t.sla_deadline <= soon:
                    return 'Próximo'
                if t.sla_deadline:
                    return 'En plazo'
                return 'Sin SLA'

            def hours_silent(t):
                ref = t.write_date or t.create_date
                if not ref:
                    return 0
                return int((now - ref).total_seconds() // 3600)

            cats = {'no_tech_reply': [], 'waiting_client': [], 'resolved_pending': [], 'other': []}
            sla_soon = []
            sla_fail = []
            for t in company_tickets:
                cats[bucket(t)].append(t)
                if t.sla_fail:
                    sla_fail.append(t)
                elif t.sla_deadline and t.sla_deadline <= soon:
                    sla_soon.append(t)

            # Destinatarios: miembros de equipos de la empresa + managers helpdesk de esa compañía
            team_users = company_tickets.mapped('team_id.member_ids')
            managers = env.ref('helpdesk.group_helpdesk_manager').user_ids.filtered(
                lambda u: trigger_company in u.company_ids and u.active
            )
            users = (team_users | managers).filtered(lambda u: u.active and u.partner_id.email)
            partners = users.mapped('partner_id')
            if not partners:
                users = env.ref('helpdesk.group_helpdesk_user').user_ids.filtered(
                    lambda u: trigger_company in u.company_ids and u.active and u.partner_id.email
                )
                partners = users.mapped('partner_id')

            web_base = env['ir.config_parameter'].sudo().get_param('web.base.url').rstrip('/')
            helpdesk_url = '%s/odoo/action-helpdesk.helpdesk_ticket_action_main_tree' % web_base
            fecha = now.strftime('%d/%m/%Y')

            rows = []
            for t in company_tickets.sorted(lambda x: (x.stage_id.sequence, x.id)):
                ticket_url = '%s/odoo/helpdesk.ticket/%s' % (web_base, t.id)
                pri = dict(t._fields['priority'].selection).get(t.priority, t.priority or '')
                last = t.write_date.strftime('%Y-%m-%d %H:%M') if t.write_date else ''
                rows.append(
                    "<tr>"
                    "<td style='padding:6px;border:1px solid #d1d5db;'><a href='%s'>%s</a></td>"
                    "<td style='padding:6px;border:1px solid #d1d5db;'>%s</td>"
                    "<td style='padding:6px;border:1px solid #d1d5db;'>%s</td>"
                    "<td style='padding:6px;border:1px solid #d1d5db;'>%s</td>"
                    "<td style='padding:6px;border:1px solid #d1d5db;'>%s</td>"
                    "<td style='padding:6px;border:1px solid #d1d5db;'>%s</td>"
                    "<td style='padding:6px;border:1px solid #d1d5db;'>%s</td>"
                    "<td style='padding:6px;border:1px solid #d1d5db;'>%s</td>"
                    "<td style='padding:6px;border:1px solid #d1d5db;'>%s</td>"
                    "<td style='padding:6px;border:1px solid #d1d5db;'>%sh</td>"
                    "<td style='padding:6px;border:1px solid #d1d5db;'>%s</td>"
                    "</tr>" % (
                        ticket_url,
                        t.ticket_ref or t.id,
                        (t.name or '')[:80].replace('<','&lt;'),
                        (t.partner_id.name or '')[:60].replace('<','&lt;'),
                        (t.company_id.name or ''),
                        (t.team_id.name or ''),
                        (t.user_id.name or 'Sin asignar'),
                        (t.stage_id.name or ''),
                        pri,
                        last,
                        hours_silent(t),
                        sla_label(t),
                    )
                )

            body = (
                "<div style='font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#111827;line-height:1.45;'>"
                "<p>Buenos días,</p>"
                "<p>A continuación se presenta el resumen de tickets que requieren seguimiento "
                "para <strong>%s</strong>.</p>"
                "<h3 style='margin:16px 0 8px;'>RESUMEN</h3>"
                "<ul>"
                "<li>Tickets sin respuesta del técnico: <strong>%s</strong></li>"
                "<li>Tickets en espera de cliente: <strong>%s</strong></li>"
                "<li>Tickets resueltos pendientes de cierre: <strong>%s</strong></li>"
                "<li>Tickets próximos a incumplir SLA: <strong>%s</strong></li>"
                "<li>Tickets vencidos por SLA: <strong>%s</strong></li>"
                "</ul>"
                "<h3 style='margin:16px 0 8px;'>TABLA</h3>"
                "<table role='presentation' width='100%%' cellpadding='0' cellspacing='0' "
                "style='border-collapse:collapse;width:100%%;max-width:1000px;font-size:13px;'>"
                "<thead>"
                "<tr style='background:#f3f4f6;'>"
                "<th style='padding:6px;border:1px solid #d1d5db;text-align:left;'>Número</th>"
                "<th style='padding:6px;border:1px solid #d1d5db;text-align:left;'>Asunto</th>"
                "<th style='padding:6px;border:1px solid #d1d5db;text-align:left;'>Cliente</th>"
                "<th style='padding:6px;border:1px solid #d1d5db;text-align:left;'>Empresa</th>"
                "<th style='padding:6px;border:1px solid #d1d5db;text-align:left;'>Equipo</th>"
                "<th style='padding:6px;border:1px solid #d1d5db;text-align:left;'>Técnico asignado</th>"
                "<th style='padding:6px;border:1px solid #d1d5db;text-align:left;'>Estado</th>"
                "<th style='padding:6px;border:1px solid #d1d5db;text-align:left;'>Prioridad</th>"
                "<th style='padding:6px;border:1px solid #d1d5db;text-align:left;'>Última actividad</th>"
                "<th style='padding:6px;border:1px solid #d1d5db;text-align:left;'>Tiempo sin respuesta</th>"
                "<th style='padding:6px;border:1px solid #d1d5db;text-align:left;'>Estado SLA</th>"
                "</tr></thead><tbody>%s</tbody></table>"
                "<p style='margin-top:20px;'>"
                "<a href='%s' style='display:inline-block;padding:12px 18px;background:#111827;color:#ffffff;"
                "text-decoration:none;border-radius:4px;font-weight:bold;'>ABRIR HELPDESK</a></p>"
                "<p style='color:#6b7280;font-size:12px;'>Recordatorio consolidado — %s. "
                "No responder a este correo.</p></div>"
            ) % (
                trigger_company.name,
                len(cats['no_tech_reply']),
                len(cats['waiting_client']),
                len(cats['resolved_pending']),
                len(sla_soon),
                len(sla_fail),
                "".join(rows),
                helpdesk_url,
                fecha,
            )

            if partners:
                env['mail.mail'].sudo().create({
                    'subject': 'Tickets pendientes de seguimiento — %s — %s' % (fecha, trigger_company.name),
                    'body_html': body,
                    'email_to': ','.join(sorted(set(partners.mapped('email')))),
                    'email_from': env['ir.config_parameter'].sudo().get_param('mail.catchall.domain') and False or env.company.email or 'dev-noreply@justech.do',
                    'auto_delete': False,
                })
                log('Digest empresa %s: %s tickets -> %s destinatarios' % (
                    trigger_company.name, len(company_tickets), len(partners)))
            else:
                log('Sin destinatarios para empresa %s' % trigger_company.name)

