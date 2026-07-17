# -*- coding: utf-8 -*-
"""Align helpdesk aliases + remove hardcoded Justech From on templates."""
import logging

_logger = logging.getLogger(__name__)

# Company-aware From: prefer company notification identity, never hardcode.
_COMPANY_FROM_EXPR = (
    "{{ (object.company_id.justech_mail_notification_from "
    "or object.company_id.email_formatted "
    "or object.user_id.email_formatted "
    "or user.email_formatted) }}"
)


def migrate(cr, version):
    env = None
    try:
        from odoo import api, SUPERUSER_ID

        env = api.Environment(cr, SUPERUSER_ID, {})
    except Exception:  # noqa: BLE001
        _logger.exception("Cannot build Environment for mail remediation migrate")
        return

    # --- FASE 1: aliases from company_id ---
    Team = env["helpdesk.team"].sudo()
    teams = Team.search([])
    teams._justech_align_alias_domain()
    _logger.info("Aligned %s helpdesk teams alias domains to company", len(teams))

    # --- FASE 3: templates hardcodes ---
    Template = env["mail.template"].sudo()
    hardcodes = Template.search(
        [
            ("model", "=", "helpdesk.ticket"),
            ("email_from", "ilike", "asistencia@justech.do"),
        ]
    )
    for tmpl in hardcodes:
        tmpl.write({"email_from": _COMPANY_FROM_EXPR})
        _logger.info("Removed hardcode From on mail.template id=%s", tmpl.id)

    # Also normalize dynamic templates that prefer team alias over company
    for tmpl in Template.search(
        [
            ("model", "=", "helpdesk.ticket"),
            ("email_from", "ilike", "team_id.alias_email_from"),
        ]
    ):
        tmpl.write({"email_from": _COMPANY_FROM_EXPR})
        _logger.info("Company-first From on mail.template id=%s", tmpl.id)

    # Ensure ICP multi-company map is present
    ICP = env["ir.config_parameter"].sudo()
    ICP.set_param("justech_mail.outgoing_policy_enabled", "True")
