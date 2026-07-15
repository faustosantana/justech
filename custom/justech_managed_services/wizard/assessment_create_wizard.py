# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class JustechMsAssessmentCreateWizard(models.TransientModel):
    _name = "justech.ms.assessment.create.wizard"
    _description = "Asistente Nuevo Levantamiento"

    step = fields.Selection(
        [
            ("client", "Cliente y plantilla"),
            ("questions", "Preguntas"),
            ("link", "Enlace"),
            ("send", "Envío"),
        ],
        default="client",
        required=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente / Empresa",
        domain="['|', ('is_company', '=', True), ('parent_id', '=', False)]",
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
    )
    consultant_id = fields.Many2one(
        "res.users",
        string="Consultor responsable",
        default=lambda self: self.env.user,
    )
    template_id = fields.Many2one(
        "justech.ms.form.template",
        string="Plantilla",
        domain="[('active', '=', True)]",
    )
    title = fields.Char(string="Título")
    email = fields.Char(string="Correo del contacto")
    phone = fields.Char(string="Teléfono")
    date_deadline = fields.Date(
        string="Vencimiento del enlace",
        default=lambda self: fields.Date.context_today(self) + timedelta(days=30),
    )
    line_ids = fields.One2many(
        "justech.ms.assessment.create.wizard.line",
        "wizard_id",
        string="Preguntas",
    )
    assessment_id = fields.Many2one("justech.managed.service.assessment", readonly=True)
    public_url = fields.Char(related="assessment_id.public_url", readonly=True)
    invite_body = fields.Text(related="assessment_id.invite_body", readonly=False)
    invite_subject = fields.Char(related="assessment_id.invite_subject", readonly=False)

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if not self.partner_id:
            self.contact_id = False
            self.email = False
            self.phone = False
            return
        company = (
            self.partner_id.commercial_company_name or self.partner_id.name or ""
        )
        self.title = _("Levantamiento de Servicios Administrados — %s", company)
        child = self.env["res.partner"].search(
            [
                ("parent_id", "=", self.partner_id.id),
                ("is_company", "=", False),
            ],
            limit=1,
        )
        if child:
            self.contact_id = child
            self.email = child.email or self.partner_id.email
            self.phone = child.phone or getattr(child, "mobile", False) or self.partner_id.phone
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

    @api.onchange("template_id")
    def _onchange_template_id(self):
        self.line_ids = [(5, 0, 0)]
        if not self.template_id:
            return
        lines = []
        for line in self.template_id.line_ids.sorted("sequence"):
            if not line.active:
                continue
            lines.append(
                (
                    0,
                    0,
                    {
                        "question_id": line.question_id.id,
                        "category_id": line.question_id.category_id.id,
                        "sequence": line.sequence,
                        "required": line.required,
                        "visible": line.visible,
                        "selected": line.visible and line.active,
                    },
                )
            )
        self.line_ids = lines

    def action_next(self):
        self.ensure_one()
        if self.step == "client":
            if not self.partner_id:
                raise UserError(_("Seleccione un cliente."))
            if not self.consultant_id:
                raise UserError(_("Seleccione un consultor."))
            if not self.template_id:
                raise UserError(_("Seleccione una plantilla."))
            if not self.line_ids:
                self._onchange_template_id()
            self.step = "questions"
        elif self.step == "questions":
            if not self.line_ids.filtered("selected"):
                raise UserError(_("Seleccione al menos una pregunta."))
            assessment = self._create_or_update_assessment()
            self.assessment_id = assessment.id
            self.step = "link"
        elif self.step == "link":
            if not self.assessment_id:
                raise UserError(_("Primero cree el levantamiento."))
            self.assessment_id.action_generate_link()
            self.step = "send"
        return self._reopen()

    def action_back(self):
        self.ensure_one()
        order = ["client", "questions", "link", "send"]
        idx = order.index(self.step)
        if idx > 0:
            self.step = order[idx - 1]
        return self._reopen()

    def action_open_assessment(self):
        self.ensure_one()
        if not self.assessment_id:
            raise UserError(_("Aún no se ha creado el levantamiento."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "justech.managed.service.assessment",
            "res_id": self.assessment_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_prepare_email(self):
        self.ensure_one()
        if not self.assessment_id:
            raise UserError(_("Genere el enlace primero."))
        return self.assessment_id.action_prepare_email()

    def action_copy_link(self):
        self.ensure_one()
        return self.assessment_id.action_copy_link_notification()

    def action_copy_message(self):
        self.ensure_one()
        return self.assessment_id.action_copy_message()

    def _create_or_update_assessment(self):
        self.ensure_one()
        Ass = self.env["justech.managed.service.assessment"]
        vals = {
            "partner_id": self.partner_id.id,
            "contact_id": self.contact_id.id,
            "consultant_id": self.consultant_id.id,
            "title": self.title
            or _(
                "Levantamiento de Servicios Administrados — %s",
                self.partner_id.name,
            ),
            "email": self.email,
            "phone": self.phone,
            "date_deadline": self.date_deadline,
            "template_id": self.template_id.id,
        }
        if self.assessment_id:
            assessment = self.assessment_id
            assessment.write(vals)
            assessment.question_line_ids.unlink()
        else:
            assessment = Ass.create(vals)

        line_vals = []
        for wline in self.line_ids.sorted("sequence"):
            if not wline.selected:
                continue
            line_vals.append(
                {
                    "assessment_id": assessment.id,
                    "question_id": wline.question_id.id,
                    "category_id": wline.category_id.id,
                    "sequence": wline.sequence,
                    "required": wline.required,
                    "active": True,
                    "visible": wline.visible,
                }
            )
        self.env["justech.ms.assessment.question.line"].create(line_vals)
        assessment.write(
            {
                "intro_text": self.template_id.intro_text,
                "closing_text": self.template_id.closing_text,
            }
        )
        return assessment

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": self.env.context,
        }


class JustechMsAssessmentCreateWizardLine(models.TransientModel):
    _name = "justech.ms.assessment.create.wizard.line"
    _description = "Línea del asistente de levantamiento"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        "justech.ms.assessment.create.wizard",
        required=True,
        ondelete="cascade",
    )
    question_id = fields.Many2one("justech.ms.form.question", required=True)
    category_id = fields.Many2one("justech.ms.form.category", required=True)
    sequence = fields.Integer(default=10)
    required = fields.Boolean()
    visible = fields.Boolean(default=True)
    selected = fields.Boolean(string="Incluir", default=True)
    question_label = fields.Char(related="question_id.name", readonly=True)
    category_name = fields.Char(related="category_id.name", readonly=True)
