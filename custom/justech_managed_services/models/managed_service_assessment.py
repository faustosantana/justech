# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
import secrets
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from html import escape

from markupsafe import Markup

from .form_schema import (
    FORM_TRACKED_KEYS,
    ORG_FIELD_MAP,
    build_sections_display,
    compute_completion_percent,
    is_value_filled,
    labels_payload,
)


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
        string="Cliente / Empresa",
        required=True,
        tracking=True,
        index=True,
        domain="['|', ('is_company', '=', True), ('parent_id', '=', False)]",
        help="Seleccione un contacto/empresa existente en Contactos. "
        "No escriba el nombre como texto libre.",
    )
    partner_vat = fields.Char(
        related="partner_id.vat",
        string="RNC",
        readonly=True,
    )
    partner_email = fields.Char(
        related="partner_id.email",
        string="Correo del cliente",
        readonly=True,
    )
    partner_phone = fields.Char(
        related="partner_id.phone",
        string="Teléfono del cliente",
        readonly=True,
    )
    contact_id = fields.Many2one(
        "res.partner",
        string="Contacto responsable",
        domain=(
            "['|', '|',"
            " ('id', '=', partner_id),"
            " ('parent_id', '=', partner_id),"
            " '&', ('is_company', '=', False),"
            " ('commercial_partner_id', '=', partner_id)]"
        ),
        help="Persona vinculada a la empresa (hijos o contactos relacionados).",
    )
    managed_service_id = fields.Many2one(
        "justech.managed.service",
        string="Servicio Administrado",
        index=True,
        copy=False,
        tracking=True,
    )
    sale_order_ids = fields.One2many(
        "sale.order",
        "justech_assessment_id",
        string="Cotizaciones",
    )
    sale_order_count = fields.Integer(
        string="Cotizaciones",
        compute="_compute_commercial_counts",
    )
    managed_service_count = fields.Integer(
        string="Servicios",
        compute="_compute_commercial_counts",
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
        default=lambda self: fields.Date.context_today(self) + timedelta(days=30),
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
    date_link_generated = fields.Datetime(string="Fecha de generación del enlace")
    date_email_sent = fields.Datetime(string="Último correo enviado")
    email_last_recipient = fields.Char(string="Último destinatario de correo")
    date_first_activity = fields.Datetime(string="Primera actividad")
    date_last_activity = fields.Datetime(string="Última actividad")
    date_done = fields.Datetime(string="Fecha de finalización")
    invite_subject = fields.Char(
        string="Asunto sugerido",
        default="Levantamiento de Servicios Administrados – Justech",
    )
    invite_body = fields.Text(
        string="Mensaje sugerido",
        help="Texto editable para correo o revisión previa al envío.",
    )
    invite_share_text = fields.Text(
        string="Mensaje para copiar",
        compute="_compute_invite_share_text",
    )
    recipient_display_name = fields.Char(
        string="Destinatario",
        compute="_compute_recipient_display",
    )
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
            ("review", "En revisión"),
            ("needs_info", "Requiere información"),
            ("approved_proposal", "Aprobado para propuesta"),
            ("opportunity_created", "Convertido a oportunidad"),
            ("quotation_ready", "Cotización preparada"),
            ("service_created", "Servicio creado"),
            ("cancel", "Cancelado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )

    SUBMITTED_STATES = (
        "done",
        "review",
        "needs_info",
        "approved_proposal",
        "opportunity_created",
        "quotation_ready",
        "service_created",
    )
    form_data = fields.Json(
        string="Respuestas del formulario",
        default=dict,
        copy=False,
    )
    answers_html = fields.Html(
        string="Respuestas formateadas",
        compute="_compute_answers_html",
        sanitize=False,
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
        closed_states = self.SUBMITTED_STATES + ("cancel",)
        for record in self:
            record.is_link_expired = bool(
                record.date_deadline
                and record.date_deadline < today
                and record.state not in closed_states
            )

    def _search_is_link_expired(self, operator, value):
        today = fields.Date.context_today(self)
        closed_states = list(self.SUBMITTED_STATES) + ["cancel"]
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

    def _compute_commercial_counts(self):
        for record in self:
            record.sale_order_count = len(record.sale_order_ids)
            if record.managed_service_id:
                record.managed_service_count = 1
            else:
                record.managed_service_count = self.env[
                    "justech.managed.service"
                ].search_count([("assessment_id", "=", record.id)])

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

    @api.depends(
        "contact_id",
        "org_responsible",
        "partner_id",
        "email",
        "phone",
        "public_url",
    )
    def _compute_invite_share_text(self):
        for record in self:
            name = (
                record.contact_id.name
                or record.org_responsible
                or record.partner_id.name
                or _("cliente")
            )
            company = record.partner_id.display_name or ""
            url = record.public_url or "[ENLACE]"
            record.invite_share_text = _(
                "Hola %(name)s,\n\n"
                "Le compartimos el levantamiento de Servicios Administrados "
                "de Justech para %(company)s.\n\n"
                "Puede completarlo y guardar su progreso en el siguiente enlace:\n\n"
                "%(url)s\n\n"
                "Quedamos atentos.\n\n"
                "Justech"
            ) % {
                "name": name,
                "company": company,
                "url": url,
            }

    @api.depends("contact_id", "org_responsible", "partner_id", "email", "phone")
    def _compute_recipient_display(self):
        for record in self:
            record.recipient_display_name = (
                record.contact_id.name
                or record.org_responsible
                or record.partner_id.name
                or False
            )

    def _suggested_title(self):
        self.ensure_one()
        company = (
            self.partner_id.commercial_company_name
            or self.partner_id.name
            or _("Cliente")
        )
        return _("Levantamiento de Servicios Administrados — %s", company)

    def _prepare_invite_body(self):
        self.ensure_one()
        name = (
            self.contact_id.name
            or self.org_responsible
            or self.partner_id.name
            or _("cliente")
        )
        company = self.partner_id.display_name or ""
        url = self.public_url or "[ENLACE]"
        closing = (
            self.consultant_id.name
            if self.consultant_id
            else _("Equipo de Justech")
        )
        return _(
            "Estimado/a %(name)s:\n\n"
            "Como parte del proceso para preparar una propuesta de servicios "
            "administrados ajustada a las necesidades de %(company)s, le invitamos "
            "a completar el siguiente levantamiento de información.\n\n"
            "Puede guardar su progreso y continuar posteriormente utilizando "
            "el mismo enlace:\n\n"
            "%(url)s\n\n"
            "La información será utilizada exclusivamente para dimensionar el "
            "alcance del servicio y será tratada de manera confidencial.\n\n"
            "Atentamente,\n\n"
            "%(closing)s"
        ) % {
            "name": name,
            "company": company,
            "url": url,
            "closing": closing,
        }

    def _refresh_invite_defaults(self):
        for record in self:
            if not record.invite_subject:
                record.invite_subject = (
                    "Levantamiento de Servicios Administrados – Justech"
                )
            record.invite_body = record._prepare_invite_body()

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
            if not vals.get("date_deadline"):
                vals["date_deadline"] = fields.Date.context_today(self) + timedelta(
                    days=30
                )
            partner_id = vals.get("partner_id")
            if partner_id:
                partner = self.env["res.partner"].browse(partner_id)
                if not vals.get("title"):
                    vals["title"] = _(
                        "Levantamiento de Servicios Administrados — %s",
                        partner.commercial_company_name or partner.name,
                    )
                if not vals.get("contact_id"):
                    defaults = self._prepare_form_defaults_from_partner(partner)
                    for key, value in defaults.items():
                        vals.setdefault(key, value)
        records = super().create(vals_list)
        for record in records:
            if record.partner_id:
                record._sync_org_fields_to_form_data()
            if not record.invite_body:
                record.invite_body = record._prepare_invite_body()
        return records

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            defaults = self._prepare_form_defaults_from_partner(self.partner_id)
            for field_name, value in defaults.items():
                setattr(self, field_name, value)
            if (
                not self.title
                or self.title.startswith(
                    "Levantamiento de Servicios Administrados"
                )
            ):
                self.title = self._suggested_title()
            if (
                self.contact_id
                and self.contact_id.commercial_partner_id
                != self.partner_id.commercial_partner_id
            ):
                self.contact_id = False
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
                self.phone = (
                    self.contact_id.phone
                    or getattr(self.contact_id, "mobile", False)
                    or self.partner_id.phone
                )
                if self.contact_id.function:
                    self.org_job = self.contact_id.function
                if self.contact_id.name:
                    self.org_responsible = self.contact_id.name
            else:
                self.email = self.partner_id.email
                self.phone = self.partner_id.phone or getattr(
                    self.partner_id, "mobile", False
                )
            self.invite_body = self._prepare_invite_body()
            if not self.invite_subject:
                self.invite_subject = (
                    "Levantamiento de Servicios Administrados – Justech"
                )
            if not self.date_deadline:
                self.date_deadline = fields.Date.context_today(self) + timedelta(
                    days=30
                )
        else:
            self.contact_id = False
            self.email = False
            self.phone = False

    @api.onchange("contact_id")
    def _onchange_contact_id(self):
        if self.contact_id:
            # Email/phone on assessment only — do not write back to res.partner.
            self.email = self.contact_id.email
            self.phone = self.contact_id.phone or getattr(
                self.contact_id, "mobile", False
            )
            if self.contact_id.function:
                self.org_job = self.contact_id.function
            if self.contact_id.name:
                self.org_responsible = self.contact_id.name
            self.invite_body = self._prepare_invite_body()
        elif self.partner_id:
            self.email = self.partner_id.email
            self.phone = self.partner_id.phone
            self.invite_body = self._prepare_invite_body()

    @api.onchange("consultant_id", "public_url")
    def _onchange_refresh_invite_body(self):
        if self.partner_id:
            self.invite_body = self._prepare_invite_body()

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
        if self.state in self.SUBMITTED_STATES:
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
        if assessment.state in assessment.SUBMITTED_STATES:
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
            data = dict(record.form_data or {})
            for key in ORG_FIELD_MAP:
                if record[key]:
                    data[key] = record[key]
            record.completion_percent = compute_completion_percent(data)

    def _assert_can_generate_link(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(
                _(
                    "Debe seleccionar un cliente o prospecto antes de "
                    "generar el enlace."
                )
            )
        if not (self.title or "").strip():
            raise UserError(
                _("Debe indicar un título antes de generar el enlace.")
            )
        if not self.consultant_id:
            raise UserError(
                _(
                    "Debe indicar el consultor responsable antes de "
                    "generar el enlace."
                )
            )
        if not self.date_deadline:
            raise UserError(
                _(
                    "Debe indicar la fecha de vencimiento del enlace "
                    "antes de generarlo."
                )
            )
        if self.state in self.SUBMITTED_STATES:
            raise UserError(
                _(
                    "El cliente ya completó el levantamiento. "
                    "El enlace está bloqueado para edición."
                )
            )
        if self.state == "cancel":
            raise UserError(_("Este levantamiento fue cancelado."))
        if self.is_link_expired:
            raise UserError(
                _(
                    "El enlace está vencido. Actualice la fecha o "
                    "regenere el enlace."
                )
            )
        if self.access_token and self.link_active:
            raise UserError(
                _("Este levantamiento ya tiene un enlace activo.")
            )

    def action_generate_link(self):
        for record in self:
            record._assert_can_generate_link()
            warnings = []
            if not (record.email or "").strip():
                warnings.append(
                    _(
                        "No se ha definido un correo de destinatario. "
                        "Puede copiar el enlace y compartirlo manualmente."
                    )
                )
            if not record.access_token:
                record.access_token = record._generate_token()
            now = fields.Datetime.now()
            vals = {
                "link_active": True,
                "date_link_generated": now,
            }
            if record.state == "draft":
                vals["state"] = "sent"
            if not record.date_sent:
                vals["date_sent"] = now
            record.write(vals)
            record.invalidate_recordset(["public_url"])
            record._refresh_invite_defaults()
            record.message_post(
                body=_(
                    "Enlace generado el %(date)s. URL: %(url)s",
                    date=now,
                    url=record.public_url,
                )
            )
            if warnings:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Enlace generado"),
                        "message": warnings[0],
                        "sticky": True,
                        "type": "warning",
                        "next": {"type": "ir.actions.act_window", "res_model": record._name, "res_id": record.id, "views": [(False, "form")], "view_mode": "form", "target": "current"},
                    },
                }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Enlace generado"),
                "message": _("Enlace activo. Puede abrirlo, copiarlo o preparar el correo."),
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": self._name,
                    "res_id": self.ids[0],
                    "views": [(False, "form")],
                    "view_mode": "form",
                    "target": "current",
                },
            },
        }

    def action_regenerate_link(self):
        for record in self:
            if record.state not in ("draft", "sent", "in_progress", "needs_info"):
                raise UserError(
                    _(
                        "Solo puede regenerar el enlace en estados Borrador, "
                        "Enviado, En proceso o Requiere información."
                    )
                )
            if record.state in record.SUBMITTED_STATES:
                raise UserError(
                    _(
                        "El cliente ya completó el levantamiento. "
                        "El enlace está bloqueado para edición."
                    )
                )
            if not record.partner_id or not record.title or not record.consultant_id:
                raise UserError(
                    _(
                        "Cliente, título y consultor son obligatorios "
                        "para regenerar el enlace."
                    )
                )
            if not record.date_deadline:
                record.date_deadline = fields.Date.context_today(record) + timedelta(
                    days=30
                )
            record.access_token = record._generate_token()
            record.link_active = True
            record.date_link_generated = fields.Datetime.now()
            if record.state == "draft":
                record.state = "sent"
            record.invalidate_recordset(["public_url"])
            record._refresh_invite_defaults()
            record.message_post(
                body=_(
                    "Enlace regenerado. El enlace anterior quedó invalidado. "
                    "Nueva URL: %s",
                    record.public_url,
                )
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Enlace regenerado"),
                "message": _("El enlace anterior quedó invalidado."),
                "type": "warning",
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": self._name,
                    "res_id": self.ids[0],
                    "views": [(False, "form")],
                    "view_mode": "form",
                    "target": "current",
                },
            },
        }

    def _clipboard_action(self, text, title):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "justech_copy_to_clipboard",
            "params": {
                "text": text or "",
                "title": title,
            },
        }

    def action_copy_link_notification(self):
        self.ensure_one()
        if not self.access_token:
            raise UserError(_("Genere el enlace antes de copiarlo."))
        self.message_post(body=_("Enlace copiado al portapapeles."))
        return self._clipboard_action(
            self.public_url,
            _("Enlace copiado"),
        )

    def action_copy_message(self):
        self.ensure_one()
        if not self.access_token:
            raise UserError(_("Genere el enlace antes de copiar el mensaje."))
        text = self.invite_share_text or self.invite_body or ""
        self.message_post(body=_("Mensaje para compartir copiado al portapapeles."))
        return self._clipboard_action(text, _("Mensaje copiado"))

    def action_open_form(self):
        self.ensure_one()
        if not self.access_token:
            raise UserError(_("Genere el enlace público primero."))
        if self.state == "cancel" or not self.link_active:
            raise UserError(_("El enlace está cancelado o inactivo."))
        if self.is_link_expired:
            raise UserError(
                _(
                    "El enlace está vencido. Actualice la fecha o "
                    "regenere el enlace."
                )
            )
        return {
            "type": "ir.actions.act_url",
            "url": self.public_url,
            "target": "new",
        }

    def _assert_email_sendable(self):
        self.ensure_one()
        if not self.access_token:
            raise UserError(
                _("No se ha generado token. Genere el enlace primero.")
            )
        if not self.link_active or self.state == "cancel":
            raise UserError(_("El enlace está cancelado o inactivo."))
        if self.is_link_expired:
            raise UserError(
                _(
                    "El enlace está vencido. Actualice la fecha o "
                    "regenere el enlace."
                )
            )
        if not (self.email or "").strip():
            raise UserError(
                _(
                    "El contacto no tiene correo. Puede copiar el enlace "
                    "y compartirlo manualmente."
                )
            )

    def _open_mail_composer(self, title):
        self.ensure_one()
        self._refresh_invite_defaults()
        template = self.env.ref(
            "justech_managed_services.mail_template_assessment_invite",
            raise_if_not_found=False,
        )
        if not template:
            raise UserError(_("No se encontró la plantilla de correo."))
        partner_ids = []
        if self.contact_id:
            partner_ids.append(self.contact_id.id)
        elif self.partner_id:
            partner_ids.append(self.partner_id.id)
        ctx = {
            "default_model": self._name,
            "default_res_ids": self.ids,
            "default_template_id": template.id,
            "default_composition_mode": "comment",
            "default_email_layout_xmlid": "mail.mail_notification_light",
            "default_partner_ids": partner_ids,
            "default_subject": self.invite_subject
            or "Levantamiento de Servicios Administrados – Justech",
            "mail_post_autofollow": False,
        }
        return {
            "type": "ir.actions.act_window",
            "name": title,
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }

    def action_prepare_email(self):
        """Abre el composer para revisión. No envía automáticamente."""
        self.ensure_one()
        if not self.access_token:
            raise UserError(_("Genere el enlace antes de preparar el correo."))
        if not (self.email or "").strip():
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Sin correo de destinatario"),
                    "message": _(
                        "El contacto no tiene correo. Puede copiar el enlace "
                        "y compartirlo manualmente."
                    ),
                    "type": "warning",
                    "sticky": True,
                },
            }
        return self._open_mail_composer(_("Preparar correo del levantamiento"))

    def action_send_email(self):
        """Abre el composer estándar (revisión obligatoria antes de enviar)."""
        self.ensure_one()
        self._assert_email_sendable()
        action = self._open_mail_composer(_("Enviar levantamiento por correo"))
        action["context"]["justech_assessment_mark_email_sent"] = True
        return action

    def action_mark_email_sent(self, recipient=None):
        """Registra envío tras usar el composer (llamable desde UI/API)."""
        for record in self:
            record.write(
                {
                    "date_email_sent": fields.Datetime.now(),
                    "email_last_recipient": recipient or record.email,
                }
            )
            record.message_post(
                body=_(
                    "Correo de levantamiento registrado hacia %(email)s.",
                    email=recipient or record.email or "-",
                )
            )
        return True

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

    def action_download_pdf(self):
        """Alias visible: Descargar PDF (mismo reporte QWeb)."""
        return self.action_print_pdf()

    def action_preview_pdf(self):
        self.ensure_one()
        return self.env.ref(
            "justech_managed_services.action_report_managed_service_assessment"
        ).report_action(self, config=False)

    def _build_opportunity_description(self):
        self.ensure_one()
        parts = [
            _("Referencia levantamiento: %s", self.name),
            _("Enlace: %s", self.public_url or "-"),
            "",
            self.summary or _("Sin resumen interno."),
        ]
        if self.org_company_name:
            parts.append(_("Empresa (formulario): %s", self.org_company_name))
        return "\n".join(parts)

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
        commercial_name = (
            partner.commercial_company_name or partner.name or self.org_company_name
        )
        opportunity = self.env["crm.lead"].create(
            {
                "name": _(
                    "Servicios Administrados — %(partner)s",
                    partner=commercial_name,
                ),
                "partner_id": partner.id,
                "contact_name": self.contact_id.name if self.contact_id else False,
                "email_from": self.email or partner.email,
                "phone": self.phone or partner.phone,
                "user_id": self.consultant_id.id if self.consultant_id else False,
                "team_id": team.id if team else False,
                "source_id": source.id,
                "description": self._build_opportunity_description(),
                "type": "opportunity",
            }
        )
        self.write(
            {
                "opportunity_id": opportunity.id,
                "state": "opportunity_created",
            }
        )
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

    def action_mark_review(self):
        for record in self:
            if record.state not in ("done", "needs_info"):
                raise UserError(
                    _("Solo puede marcar en revisión un levantamiento completado.")
                )
            record.state = "review"
        return True

    def action_request_info(self):
        for record in self:
            if record.state not in ("done", "review", "approved_proposal"):
                raise UserError(
                    _("Solo aplica solicitar información desde Completado o En revisión.")
                )
            record.write({"state": "needs_info", "link_active": True})
            record.message_post(body=_("Se solicitó información adicional al cliente."))
        return True

    def action_approve_for_proposal(self):
        for record in self:
            if record.state not in ("done", "review", "needs_info"):
                raise UserError(
                    _(
                        "Apruebe para propuesta solo desde Completado, "
                        "En revisión o Requiere información."
                    )
                )
            record.state = "approved_proposal"
            record.message_post(body=_("Levantamiento aprobado para propuesta comercial."))
        return True

    def action_create_quotation(self):
        self.ensure_one()
        existing = self.sale_order_ids.filtered(
            lambda o: o.state in ("draft", "sent")
        )
        if existing:
            return {
                "type": "ir.actions.act_window",
                "name": _("Cotizaciones"),
                "res_model": "sale.order",
                "view_mode": "list,form",
                "domain": [("id", "in", existing.ids)],
                "target": "current",
            }
        if not self.opportunity_id:
            self.action_create_opportunity()
        partner = self.partner_id
        note_parts = [
            _("Levantamiento: %s", self.name),
            self.summary or "",
        ]
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "partner_invoice_id": partner.id,
                "partner_shipping_id": partner.id,
                "opportunity_id": self.opportunity_id.id,
                "origin": self.name,
                "client_order_ref": self.name,
                "user_id": self.consultant_id.id or self.env.user.id,
                "justech_assessment_id": self.id,
                "justech_managed_service_id": self.managed_service_id.id,
                "note": "\n".join(p for p in note_parts if p),
            }
        )
        self.write({"state": "quotation_ready"})
        self.message_post(
            body=_("Cotización creada: %s (sin líneas; agregue productos).", order.name)
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": order.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_quotations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Cotizaciones"),
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [
                "|",
                ("justech_assessment_id", "=", self.id),
                ("opportunity_id", "=", self.opportunity_id.id),
            ]
            if self.opportunity_id
            else [("justech_assessment_id", "=", self.id)],
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_justech_assessment_id": self.id,
                "default_opportunity_id": self.opportunity_id.id,
            },
        }

    def action_open_quotation(self):
        self.ensure_one()
        order = self.sale_order_ids[:1]
        if not order and self.opportunity_id:
            order = self.env["sale.order"].search(
                [("opportunity_id", "=", self.opportunity_id.id)], limit=1
            )
        if not order:
            raise UserError(_("No hay cotización vinculada. Use Crear cotización."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": order.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_create_managed_service(self):
        self.ensure_one()
        if self.managed_service_id:
            return self.action_open_managed_service()
        existing = self.env["justech.managed.service"].search(
            [("assessment_id", "=", self.id)], limit=1
        )
        if existing:
            self.managed_service_id = existing
            return self.action_open_managed_service()
        opportunity = self.opportunity_id
        sale_order = self.sale_order_ids[:1]
        won = False
        if opportunity:
            stage = opportunity.stage_id
            won = bool(
                getattr(stage, "is_won", False)
                or opportunity.probability >= 100
            )
        if sale_order and sale_order.state in ("sale", "done"):
            initial_state = "implementation"
        elif won:
            initial_state = "approved"
        else:
            initial_state = "approved"
        partner = self.partner_id.commercial_partner_id
        # Prefill from form seed
        data = self.form_data or {}
        levels = data.get("support_levels") or []
        outsource = data.get("outsource_services") or []
        service = self.env["justech.managed.service"].create(
            {
                "title": _(
                    "Servicios Administrados — %(partner)s",
                    partner=partner.commercial_company_name or partner.name,
                ),
                "partner_id": partner.id,
                "contact_id": self.contact_id.id,
                "company_id": self.company_id.id,
                "salesperson_id": opportunity.user_id.id
                if opportunity and opportunity.user_id
                else self.consultant_id.id,
                "technician_id": self.consultant_id.id,
                "opportunity_id": opportunity.id if opportunity else False,
                "assessment_id": self.id,
                "sale_order_id": sale_order.id if sale_order else False,
                "state": initial_state,
                "level_l1": "nivel_1" in levels or True,
                "level_l2": "nivel_2" in levels,
                "level_l3": "nivel_3" in levels,
                "support_remote": "soporte_remoto" in outsource,
                "support_onsite": "soporte_presencial" in outsource,
                "scope_notes": self.summary or False,
            }
        )
        if opportunity:
            opportunity.justech_managed_service_id = service.id
        if sale_order:
            sale_order.justech_managed_service_id = service.id
        self.write(
            {
                "managed_service_id": service.id,
                "state": "service_created",
            }
        )
        self.message_post(
            body=_("Servicio Administrado creado: %s", service.name)
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "justech.managed.service",
            "res_id": service.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_managed_service(self):
        self.ensure_one()
        service = self.managed_service_id or self.env[
            "justech.managed.service"
        ].search([("assessment_id", "=", self.id)], limit=1)
        if not service:
            raise UserError(_("No hay Servicio Administrado vinculado."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "justech.managed.service",
            "res_id": service.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_partner(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("No hay cliente seleccionado."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.partner_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_contact(self):
        self.ensure_one()
        if not self.contact_id:
            raise UserError(_("No hay contacto responsable seleccionado."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.contact_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_mark_reviewed(self):
        """Compatibilidad: 'Marcar revisado' → En revisión."""
        return self.action_mark_review()

    def action_reopen_public(self):
        if not self.env.user.has_group(
            "justech_managed_services.group_ms_manager"
        ):
            raise UserError(
                _("Solo un administrador puede reabrir el formulario público.")
            )
        reopenable = ("done", "review", "needs_info", "approved_proposal")
        for record in self:
            if record.state not in reopenable:
                raise UserError(
                    _(
                        "Solo puede reabrir levantamientos completados, "
                        "en revisión, que requieren información o aprobados."
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
            record.message_post(body=_("Enlace público cancelado / invalidado."))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Enlace cancelado"),
                "message": _("El enlace público quedó inactivo."),
                "type": "warning",
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": self._name,
                    "res_id": self.ids[0],
                    "views": [(False, "form")],
                    "view_mode": "form",
                    "target": "current",
                },
            },
        }

    def action_cancel(self):
        for record in self:
            record.write({"state": "cancel", "link_active": False})
            record.message_post(body=_("Levantamiento cancelado."))
        return True

    def unlink(self):
        protected_states = self.SUBMITTED_STATES
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

    def _compute_answers_html(self):
        for record in self:
            chunks = []
            for section in record.get_form_print_sections():
                chunks.append("<h3>%s</h3>" % escape(section["heading"]))
                if not section["rows"]:
                    chunks.append("<p><em>Sin respuestas.</em></p>")
                    continue
                chunks.append("<ul>")
                for row in section["rows"]:
                    chunks.append(
                        "<li><strong>%s:</strong> %s</li>"
                        % (escape(row["label"]), escape(row["value"]))
                    )
                chunks.append("</ul>")
            record.answers_html = Markup("".join(chunks))

    def get_form_display_values(self):
        """Valores crudos para prefill del formulario público."""
        self.ensure_one()
        data = dict(self.form_data or {})
        for key in ORG_FIELD_MAP:
            if self[key]:
                data.setdefault(key, self[key])
        return data

    def get_form_labels_payload(self):
        """Etiquetas centralizadas para JS (revisión pública)."""
        return labels_payload()

    def get_form_print_sections(self):
        """Secciones con etiquetas/valores legibles para resumen, backend y PDF."""
        self.ensure_one()
        return build_sections_display(self.get_form_display_values())

    def get_form_answers_matrix(self):
        """Matriz de verificación sección → valor (UAT / auditoría)."""
        self.ensure_one()
        matrix = []
        for section in self.get_form_print_sections():
            matrix.append(
                {
                    "section": section["heading"],
                    "answers": [
                        {
                            "key": row["key"],
                            "label": row["label"],
                            "value": row["value"],
                            "filled": is_value_filled(row["raw"])
                            or row["type"] == "boolean",
                        }
                        for row in section["rows"]
                    ],
                    "has_answers": bool(section["rows"]),
                }
            )
        return matrix
