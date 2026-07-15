# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
import secrets
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .form_schema import FORM_TRACKED_KEYS, ORG_FIELD_MAP


class JustechManagedServiceAssessment(models.Model):
    _name = "justech.managed.service.assessment"
    _description = "Levantamiento de Servicios Administrados"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Referencia",
        required=True,
        copy=False,
        default=lambda self: _("Nuevo"),
        readonly=True,
    )
    title = fields.Char(string="Título del levantamiento")
    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente / Prospecto",
        required=True,
        tracking=True,
        index=True,
    )
    contact_id = fields.Many2one(
        "res.partner",
        string="Contacto responsable",
        domain="[('parent_id', '=', partner_id), ('is_company', '=', False)]",
    )
    email = fields.Char(string="Correo electrónico")
    phone = fields.Char(string="Teléfono")
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    consultant_id = fields.Many2one(
        "res.users",
        string="Consultor responsable",
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
    )
    opportunity_id = fields.Many2one(
        "crm.lead",
        string="Oportunidad CRM",
        tracking=True,
        index=True,
    )
    date_deadline = fields.Date(
        string="Vencimiento del enlace",
        tracking=True,
    )
    access_token = fields.Char(
        string="Token de acceso",
        copy=False,
        index=True,
    )
    public_url = fields.Char(
        string="Enlace público",
        compute="_compute_public_url",
    )
    link_active = fields.Boolean(
        string="Enlace activo",
        default=True,
        tracking=True,
    )
    completion_percent = fields.Float(
        string="Completado (%)",
        digits=(5, 2),
    )
    date_sent = fields.Datetime(string="Fecha de envío")
    date_first_activity = fields.Datetime(string="Primera actividad")
    date_last_activity = fields.Datetime(string="Última actividad")
    date_done = fields.Datetime(string="Fecha de finalización")
    internal_notes = fields.Html(string="Observaciones internas")
    summary = fields.Text(string="Resumen del levantamiento")
    completed_by_name = fields.Char(string="Completado por")
    completed_by_job = fields.Char(string="Cargo")
    acceptance_date = fields.Date(string="Fecha de aceptación")
    acceptance_confirmed = fields.Boolean(string="Aceptación confirmada")
    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("sent", "Enviado"),
            ("in_progress", "En proceso"),
            ("done", "Completado"),
            ("reviewed", "Revisado"),
            ("proposal_ready", "Propuesta preparada"),
            ("cancel", "Cancelado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    form_data = fields.Json(
        string="Respuestas del formulario",
        default=dict,
        copy=False,
    )
    org_company_name = fields.Char(string="Empresa (formulario)")
    org_vat = fields.Char(string="RNC (formulario)")
    org_address = fields.Char(string="Dirección (formulario)")
    org_responsible = fields.Char(string="Responsable (formulario)")
    org_job = fields.Char(string="Cargo (formulario)")
    org_email = fields.Char(string="Correo (formulario)")
    org_phone = fields.Char(string="Teléfono (formulario)")
    is_link_expired = fields.Boolean(
        string="Enlace vencido",
        compute="_compute_is_link_expired",
        search="_search_is_link_expired",
    )

    @api.depends("date_deadline", "state")
    def _compute_is_link_expired(self):
        today = fields.Date.context_today(self)
        closed_states = ("done", "reviewed", "proposal_ready", "cancel")
        for record in self:
            record.is_link_expired = bool(
                record.date_deadline
                and record.date_deadline < today
                and record.state not in closed_states
            )

    def _search_is_link_expired(self, operator, value):
        today = fields.Date.context_today(self)
        closed_states = ("done", "reviewed", "proposal_ready", "cancel")
        if (operator, value) in (("=", True), ("!=", False)):
            return [
                ("date_deadline", "<", today),
                ("state", "not in", list(closed_states)),
            ]
        if (operator, value) in (("=", False), ("!=", True)):
            return [
                "|",
                ("date_deadline", "=", False),
                "|",
                ("date_deadline", ">=", today),
                ("state", "in", list(closed_states)),
            ]
        return []

    @api.depends("access_token")
    def _compute_public_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for record in self:
            if record.access_token:
                record.public_url = (
                    f"{base_url}/servicios/levantamiento/{record.access_token}"
                )
            else:
                record.public_url = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "justech.managed.service.assessment"
                    )
                    or _("Nuevo")
                )
            partner_id = vals.get("partner_id")
            if partner_id and not vals.get("contact_id"):
                partner = self.env["res.partner"].browse(partner_id)
                defaults = self._prepare_form_defaults_from_partner(partner)
                for key, value in defaults.items():
                    vals.setdefault(key, value)
        records = super().create(vals_list)
        for record in records:
            if record.partner_id:
                record._sync_org_fields_to_form_data()
        return records

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            defaults = self._prepare_form_defaults_from_partner(self.partner_id)
            for field_name, value in defaults.items():
                setattr(self, field_name, value)
            if not self.contact_id and self.partner_id.is_company:
                child = self.env["res.partner"].search(
                    [
                        ("parent_id", "=", self.partner_id.id),
                        ("is_company", "=", False),
                    ],
                    limit=1,
                )
                if child:
                    self.contact_id = child
            if self.contact_id:
                self.email = self.contact_id.email or self.partner_id.email
                self.phone = self.contact_id.phone or self.partner_id.phone
            else:
                self.email = self.partner_id.email
                self.phone = self.partner_id.phone

    @api.onchange("contact_id")
    def _onchange_contact_id(self):
        if self.contact_id:
            self.email = self.contact_id.email
            self.phone = self.contact_id.phone or getattr(
                self.contact_id, "mobile", False
            )
            if self.contact_id.function:
                self.org_job = self.contact_id.function
            if self.contact_id.name:
                self.org_responsible = self.contact_id.name

    def _prepare_form_defaults_from_partner(self, partner):
        partner = partner.sudo()
        address_parts = [
            part
            for part in [
                partner.street,
                partner.street2,
                partner.city,
                partner.state_id.name if partner.state_id else False,
                partner.country_id.name if partner.country_id else False,
            ]
            if part
        ]
        return {
            "org_company_name": partner.commercial_company_name or partner.name,
            "org_vat": partner.vat or False,
            "org_address": ", ".join(address_parts) if address_parts else False,
            "org_responsible": partner.name if not partner.is_company else False,
            "org_job": partner.function or False,
            "org_email": partner.email or False,
            "org_phone": partner.phone
            or getattr(partner, "mobile", False)
            or False,
        }

    def _sync_org_fields_to_form_data(self):
        for record in self:
            data = dict(record.form_data or {})
            for field_name in ORG_FIELD_MAP:
                value = record[field_name]
                if value:
                    data[field_name] = value
            record.form_data = data

    def _generate_token(self):
        return secrets.token_urlsafe(32)

    def _ensure_editable_public(self):
        self.ensure_one()
        if self.state == "cancel":
            raise ValidationError(_("Este levantamiento fue cancelado."))
        if not self.link_active:
            raise ValidationError(_("El enlace público está inactivo."))
        if self.date_deadline and self.date_deadline < fields.Date.context_today(self):
            raise ValidationError(_("El enlace público ha vencido."))
        if self.state in ("done", "reviewed", "proposal_ready"):
            raise ValidationError(_("Este levantamiento ya fue enviado."))

    @api.model
    def public_get_by_token(self, token):
        if not token:
            return self.browse(), "invalid"
        assessment = self.sudo().search([("access_token", "=", token)], limit=1)
        if not assessment:
            return self.browse(), "invalid"
        if assessment.state == "cancel":
            return assessment, "cancelled"
        if assessment.state in ("done", "reviewed", "proposal_ready"):
            return assessment, "submitted"
        if not assessment.link_active:
            return assessment, "inactive"
        if (
            assessment.date_deadline
            and assessment.date_deadline < fields.Date.context_today(assessment)
        ):
            return assessment, "expired"
        return assessment, "ok"

    def _merge_public_form_data(self, vals):
        self.ensure_one()
        data = dict(self.form_data or {})
        org_keys = set(ORG_FIELD_MAP.keys())
        for key, value in vals.items():
            if key in org_keys:
                if key in self._fields:
                    self[key] = value
                data[key] = value
            elif key in FORM_TRACKED_KEYS or key.startswith("section_"):
                data[key] = value
        self.form_data = data
        self._compute_completion_from_form_data()

    def public_save_partial(self, vals):
        self.ensure_one()
        self._ensure_editable_public()
        now = fields.Datetime.now()
        self._merge_public_form_data(vals or {})
        write_vals = {
            "state": "in_progress" if self.state in ("draft", "sent") else self.state,
            "date_last_activity": now,
            "completion_percent": self.completion_percent,
        }
        if not self.date_first_activity:
            write_vals["date_first_activity"] = now
        self.sudo().write(write_vals)
        return {
            "state": self.state,
            "completion_percent": self.completion_percent,
        }

    def public_submit(self, vals):
        self.ensure_one()
        self._ensure_editable_public()
        vals = dict(vals or {})
        acceptance = vals.pop("acceptance_confirmed", False)
        completed_by_name = vals.pop("completed_by_name", False)
        completed_by_job = vals.pop("completed_by_job", False)
        if not acceptance:
            raise ValidationError(
                _(
                    "Debe confirmar que la información representa razonablemente "
                    "el entorno tecnológico de la organización."
                )
            )
        if not completed_by_name or not completed_by_job:
            raise ValidationError(
                _("Indique el nombre y cargo de quien completa el levantamiento.")
            )
        self._merge_public_form_data(vals)
        now = fields.Datetime.now()
        today = fields.Date.context_today(self)
        self.sudo().write(
            {
                "state": "done",
                "date_done": now,
                "date_last_activity": now,
                "date_first_activity": self.date_first_activity or now,
                "completed_by_name": completed_by_name,
                "completed_by_job": completed_by_job,
                "acceptance_confirmed": True,
                "acceptance_date": today,
                "link_active": False,
                "completion_percent": 100.0,
            }
        )
        self.sudo().message_post(
            body=_(
                "Levantamiento completado por %(name)s (%(job)s).",
                name=completed_by_name,
                job=completed_by_job,
            ),
            message_type="notification",
            subtype_xmlid="mail.mt_note",
        )
        if self.consultant_id:
            self.sudo().activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=self.consultant_id.id,
                summary=_("Levantamiento completado: %s", self.name),
            )
        return {"state": self.state}

    def _compute_completion_from_form_data(self):
        for record in self:
            total = len(FORM_TRACKED_KEYS) + len(ORG_FIELD_MAP)
            if not total:
                record.completion_percent = 0.0
                continue
            filled = 0
            data = record.form_data or {}
            for key in ORG_FIELD_MAP:
                if record[key] or data.get(key):
                    filled += 1
            for key in FORM_TRACKED_KEYS:
                value = data.get(key)
                if value not in (None, False, "", [], {}):
                    filled += 1
            record.completion_percent = round((filled / total) * 100.0, 2)

    def action_generate_link(self):
        for record in self:
            if not record.access_token:
                record.access_token = record._generate_token()
            if record.state == "draft":
                record.state = "sent"
            if not record.date_sent:
                record.date_sent = fields.Datetime.now()
            if not record.date_deadline:
                record.date_deadline = fields.Date.context_today(record) + timedelta(
                    days=30
                )
            record.link_active = True
        return True

    def action_regenerate_link(self):
        for record in self:
            if record.state not in ("draft", "sent", "in_progress"):
                raise UserError(
                    _(
                        "Solo puede regenerar el enlace en estados Borrador, "
                        "Enviado o En proceso."
                    )
                )
            record.access_token = record._generate_token()
            record.link_active = True
        return True

    def action_copy_link_notification(self):
        self.ensure_one()
        if not self.access_token:
            raise UserError(_("Genere el enlace antes de copiarlo."))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Enlace del levantamiento"),
                "message": self.public_url,
                "sticky": True,
                "type": "success",
            },
        }

    def action_open_form(self):
        self.ensure_one()
        if not self.access_token:
            raise UserError(_("Genere el enlace público primero."))
        return {
            "type": "ir.actions.act_url",
            "url": self.public_url,
            "target": "new",
        }

    def action_send_email(self):
        self.ensure_one()
        if not self.access_token:
            self.action_generate_link()
        template = self.env.ref(
            "justech_managed_services.mail_template_assessment_invite",
            raise_if_not_found=False,
        )
        if not template:
            raise UserError(_("No se encontró la plantilla de correo."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Enviar levantamiento"),
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_model": self._name,
                "default_res_ids": self.ids,
                "default_template_id": template.id,
                "default_composition_mode": "comment",
                "default_email_layout_xmlid": "mail.mail_notification_light",
            },
        }

    def action_view_answers(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Respuestas del levantamiento"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "views": [
                (
                    self.env.ref(
                        "justech_managed_services.view_justech_managed_service_assessment_answers_form"
                    ).id,
                    "form",
                )
            ],
            "target": "current",
        }

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref(
            "justech_managed_services.action_report_managed_service_assessment"
        ).report_action(self)

    def _get_or_create_utm_source(self):
        source_name = _("Levantamiento de Servicios Administrados")
        source = self.env["utm.source"].sudo().search(
            [("name", "=", source_name)], limit=1
        )
        if not source:
            source = self.env["utm.source"].sudo().create({"name": source_name})
        return source

    def action_create_opportunity(self):
        self.ensure_one()
        if self.opportunity_id:
            return self.action_open_opportunity()
        partner = self.partner_id
        source = self._get_or_create_utm_source()
        team = self.env["crm.team"]._get_default_team_id(user_id=self.env.uid)
        opportunity = self.env["crm.lead"].create(
            {
                "name": _(
                    "Servicios Administrados — %(partner)s",
                    partner=partner.display_name,
                ),
                "partner_id": partner.id,
                "contact_name": self.contact_id.name if self.contact_id else False,
                "email_from": self.email or partner.email,
                "phone": self.phone or partner.phone,
                "user_id": self.consultant_id.id if self.consultant_id else False,
                "team_id": team.id if team else False,
                "source_id": source.id,
                "description": _(
                    "Oportunidad generada desde el levantamiento %(ref)s.",
                    ref=self.name,
                ),
                "type": "opportunity",
            }
        )
        self.opportunity_id = opportunity
        self.message_post(
            body=_(
                "Oportunidad CRM creada: %(name)s",
                name=opportunity.display_name,
            )
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "crm.lead",
            "res_id": opportunity.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_opportunity(self):
        self.ensure_one()
        if not self.opportunity_id:
            raise UserError(_("No hay oportunidad vinculada."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "crm.lead",
            "res_id": self.opportunity_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_mark_reviewed(self):
        for record in self:
            if record.state != "done":
                raise UserError(
                    _("Solo puede marcar como revisado un levantamiento completado.")
                )
            record.state = "reviewed"
        return True

    def action_reopen_public(self):
        if not self.env.user.has_group(
            "justech_managed_services.group_ms_manager"
        ):
            raise UserError(
                _("Solo un administrador puede reabrir el formulario público.")
            )
        for record in self:
            if record.state not in ("done", "reviewed", "proposal_ready"):
                raise UserError(
                    _(
                        "Solo puede reabrir levantamientos completados, "
                        "revisados o con propuesta preparada."
                    )
                )
            record.write(
                {
                    "state": "in_progress",
                    "link_active": True,
                    "acceptance_confirmed": False,
                }
            )
            record.message_post(body=_("Formulario público reabierto."))
        return True

    def action_invalidate_link(self):
        for record in self:
            record.link_active = False
            record.message_post(body=_("Enlace público invalidado."))
        return True

    def action_cancel(self):
        for record in self:
            record.write({"state": "cancel", "link_active": False})
            record.message_post(body=_("Levantamiento cancelado."))
        return True

    def unlink(self):
        protected_states = ("done", "reviewed", "proposal_ready")
        is_manager = self.env.user.has_group(
            "justech_managed_services.group_ms_manager"
        )
        for record in self:
            if record.state in protected_states and not is_manager:
                raise UserError(
                    _(
                        "No puede eliminar levantamientos completados o revisados. "
                        "Contacte a un administrador de Servicios Administrados."
                    )
                )
        return super().unlink()

    def get_form_display_values(self):
        """Valores para plantillas públicas y PDF."""
        self.ensure_one()
        data = dict(self.form_data or {})
        for key in ORG_FIELD_MAP:
            if self[key]:
                data.setdefault(key, self[key])
        return data
