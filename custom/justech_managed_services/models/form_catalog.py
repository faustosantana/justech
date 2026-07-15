# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
"""Catálogo, plantillas y líneas de preguntas para levantamientos configurables."""
import json

from odoo import _, api, fields, models

from .form_schema import FORM_FIELDS, SECTION_LABELS, format_field_value, is_value_filled


# Plantillas: code -> secciones (números 1-16) incluidas. Vacío = todas.
TEMPLATE_SECTION_MAP = {
    "servicios_administrados": list(range(1, 17)),
    "soporte_tecnico": [1, 2, 4, 7, 8, 10, 11, 12, 16],
    "microsoft_365": [1, 2, 5, 6, 7, 8, 12, 13, 16],
    "google_workspace": [1, 2, 5, 6, 7, 8, 12, 13, 16],
    "azure": [1, 2, 4, 5, 6, 7, 8, 12, 13, 16],
    "redes": [1, 3, 4, 5, 6, 8, 12, 13, 16],
    "ciberseguridad": [1, 2, 5, 6, 7, 12, 13, 14, 16],
    "cctv": [1, 3, 4, 5, 6, 8, 12, 13, 16],
    "infraestructura": [1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 16],
    "licenciamiento": [1, 2, 5, 6, 15, 16],
    "consultoria": [1, 2, 6, 11, 12, 14, 15, 16],
    "desarrollo_software": [1, 2, 5, 6, 14, 15, 16],
}

TEMPLATE_META = {
    "servicios_administrados": {
        "name": "Servicios Administrados",
        "intro": "Levantamiento integral para dimensionar una iguala / servicio administrado.",
        "closing": "Gracias por completar la información. El equipo Justech preparará una propuesta ajustada.",
    },
    "soporte_tecnico": {
        "name": "Soporte Técnico",
        "intro": "Levantamiento enfocado en mesa de ayuda y soporte operativo.",
        "closing": "Con esta información diseñaremos el servicio de soporte adecuado.",
    },
    "microsoft_365": {
        "name": "Microsoft 365",
        "intro": "Diagnóstico para administración y soporte de Microsoft 365.",
        "closing": "Usaremos estas respuestas para proponer el plan de gestión M365.",
    },
    "google_workspace": {
        "name": "Google Workspace",
        "intro": "Diagnóstico para administración y soporte de Google Workspace.",
        "closing": "Usaremos estas respuestas para proponer el plan de gestión Workspace.",
    },
    "azure": {
        "name": "Azure",
        "intro": "Levantamiento de nube e infraestructura sobre Microsoft Azure.",
        "closing": "Gracias. Prepararemos recomendaciones sobre Azure.",
    },
    "redes": {
        "name": "Redes",
        "intro": "Evaluación de conectividad, oficinas y equipos de red.",
        "closing": "Con esta base dimensionaremos el servicio de redes.",
    },
    "ciberseguridad": {
        "name": "Ciberseguridad",
        "intro": "Levantamiento de postura de seguridad y cumplimiento.",
        "closing": "Gracias. Elaboraremos recomendaciones de ciberseguridad.",
    },
    "cctv": {
        "name": "CCTV",
        "intro": "Levantamiento para soluciones de videovigilancia.",
        "closing": "Usaremos estos datos para diseñar la solución CCTV.",
    },
    "infraestructura": {
        "name": "Infraestructura",
        "intro": "Diagnóstico de servidores, sitios y plataformas de infraestructura.",
        "closing": "Prepararemos una propuesta de infraestructura a medida.",
    },
    "licenciamiento": {
        "name": "Licenciamiento",
        "intro": "Inventario y necesidades de licenciamiento de software.",
        "closing": "Con esta información propondremos opciones de licenciamiento.",
    },
    "consultoria": {
        "name": "Consultoría",
        "intro": "Levantamiento para servicios de consultoría TI.",
        "closing": "Gracias. Diseñaremos el alcance de consultoría.",
    },
    "desarrollo_software": {
        "name": "Desarrollo de Software",
        "intro": "Levantamiento de necesidades para proyectos de desarrollo.",
        "closing": "Usaremos estas respuestas para estimar el proyecto.",
    },
}


class JustechMsFormCategory(models.Model):
    _name = "justech.ms.form.category"
    _description = "Categoría de levantamiento"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text()
    question_ids = fields.One2many(
        "justech.ms.form.question", "category_id", string="Preguntas"
    )
    question_count = fields.Integer(compute="_compute_question_count")

    _sql_constraints = [
        ("code_uniq", "unique(code)", "El código de categoría debe ser único."),
    ]

    def _compute_question_count(self):
        for rec in self:
            rec.question_count = len(rec.question_ids)


class JustechMsFormQuestion(models.Model):
    _name = "justech.ms.form.question"
    _description = "Pregunta reutilizable de levantamiento"
    _order = "category_id, sequence, id"

    name = fields.Char(string="Etiqueta", required=True, translate=True)
    key = fields.Char(
        string="Clave técnica",
        required=True,
        index=True,
        help="Identificador estable usado en respuestas (form_data).",
    )
    category_id = fields.Many2one(
        "justech.ms.form.category",
        required=True,
        ondelete="restrict",
        index=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    field_type = fields.Selection(
        [
            ("char", "Texto corto"),
            ("text", "Texto largo"),
            ("number", "Número"),
            ("select", "Selección"),
            ("multiselect", "Selección múltiple"),
            ("boolean", "Sí / No"),
        ],
        required=True,
        default="char",
    )
    options_json = fields.Text(
        string="Opciones (JSON)",
        help='Objeto {"valor": "Etiqueta"} para select/multiselect.',
    )
    help_text = fields.Char(string="Ayuda")
    storage = fields.Selection(
        [("json", "JSON"), ("column", "Columna org_*"), ("meta", "Meta")],
        default="json",
        required=True,
    )
    section_number = fields.Integer(string="Sección origen")

    _sql_constraints = [
        ("key_uniq", "unique(key)", "La clave de pregunta debe ser única."),
    ]

    def get_options_dict(self):
        self.ensure_one()
        if not self.options_json:
            return {}
        try:
            data = json.loads(self.options_json)
            return data if isinstance(data, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}


class JustechMsFormTemplate(models.Model):
    _name = "justech.ms.form.template"
    _description = "Plantilla de levantamiento"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    intro_text = fields.Html(string="Texto inicial", sanitize_style=True)
    closing_text = fields.Html(string="Texto final", sanitize_style=True)
    line_ids = fields.One2many(
        "justech.ms.form.template.line",
        "template_id",
        string="Preguntas",
        copy=True,
    )
    line_count = fields.Integer(compute="_compute_line_count")

    _sql_constraints = [
        ("code_uniq", "unique(code)", "El código de plantilla debe ser único."),
    ]

    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    def action_open_lines(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Preguntas de la plantilla"),
            "res_model": "justech.ms.form.template.line",
            "view_mode": "list,form",
            "domain": [("template_id", "=", self.id)],
            "context": {"default_template_id": self.id},
        }

    def copy_lines_to_assessment(self, assessment):
        """Copia líneas activas de la plantilla al levantamiento."""
        self.ensure_one()
        AssessmentLine = self.env["justech.ms.assessment.question.line"]
        assessment.question_line_ids.unlink()
        vals_list = []
        for line in self.line_ids.sorted("sequence"):
            if not line.active or not line.question_id.active:
                continue
            vals_list.append(
                {
                    "assessment_id": assessment.id,
                    "question_id": line.question_id.id,
                    "category_id": line.question_id.category_id.id,
                    "sequence": line.sequence,
                    "required": line.required,
                    "active": True,
                    "visible": line.visible,
                }
            )
        if vals_list:
            AssessmentLine.create(vals_list)
        assessment.write(
            {
                "template_id": self.id,
                "intro_text": self.intro_text,
                "closing_text": self.closing_text,
            }
        )
        return True


class JustechMsFormTemplateLine(models.Model):
    _name = "justech.ms.form.template.line"
    _description = "Línea de plantilla de levantamiento"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "justech.ms.form.template",
        required=True,
        ondelete="cascade",
        index=True,
    )
    question_id = fields.Many2one(
        "justech.ms.form.question",
        required=True,
        ondelete="restrict",
        index=True,
    )
    category_id = fields.Many2one(
        related="question_id.category_id",
        store=True,
        readonly=True,
    )
    sequence = fields.Integer(default=10)
    required = fields.Boolean(string="Obligatoria", default=False)
    active = fields.Boolean(default=True)
    visible = fields.Boolean(
        string="Visible",
        default=True,
        help="Si se desactiva, la pregunta no aparece en el formulario público.",
    )
    question_label = fields.Char(related="question_id.name", readonly=True)
    field_type = fields.Selection(related="question_id.field_type", readonly=True)


class JustechMsAssessmentQuestionLine(models.Model):
    _name = "justech.ms.assessment.question.line"
    _description = "Pregunta activa en un levantamiento"
    _order = "sequence, id"

    assessment_id = fields.Many2one(
        "justech.managed.service.assessment",
        required=True,
        ondelete="cascade",
        index=True,
    )
    question_id = fields.Many2one(
        "justech.ms.form.question",
        required=True,
        ondelete="restrict",
        index=True,
    )
    category_id = fields.Many2one(
        "justech.ms.form.category",
        required=True,
        ondelete="restrict",
        index=True,
    )
    sequence = fields.Integer(default=10)
    required = fields.Boolean(default=False)
    active = fields.Boolean(default=True)
    visible = fields.Boolean(default=True)
    key = fields.Char(related="question_id.key", store=True, readonly=True)
    question_label = fields.Char(related="question_id.name", readonly=True)
    field_type = fields.Selection(related="question_id.field_type", readonly=True)

    def name_get(self):
        return [(rec.id, rec.question_label or rec.key or str(rec.id)) for rec in self]


class JustechMsFormTemplateSeed(models.AbstractModel):
    _name = "justech.ms.form.seed"
    _description = "Utilidad de semilla de catálogo"

    @api.model
    def seed_catalog(self):
        return seed_form_catalog(self.env)


def seed_form_catalog(env):
    """Crea categorías, preguntas y plantillas desde form_schema (idempotente)."""
    Category = env["justech.ms.form.category"].sudo()
    Question = env["justech.ms.form.question"].sudo()
    Template = env["justech.ms.form.template"].sudo()
    Line = env["justech.ms.form.template.line"].sudo()

    categories = {}
    for number, label in SECTION_LABELS.items():
        code = "sec_%02d" % number
        cat = Category.search([("code", "=", code)], limit=1)
        if not cat:
            cat = Category.create(
                {
                    "name": label,
                    "code": code,
                    "sequence": number * 10,
                }
            )
        else:
            cat.write({"name": label, "sequence": number * 10, "active": True})
        categories[number] = cat

    questions = {}
    seq_by_cat = {n: 0 for n in categories}
    for key, meta in FORM_FIELDS.items():
        if meta.get("storage") == "meta":
            continue
        section = meta.get("section") or 1
        cat = categories.get(section) or categories[1]
        seq_by_cat[section] = seq_by_cat.get(section, 0) + 10
        options = meta.get("options") or {}
        vals = {
            "name": meta["label"],
            "key": key,
            "category_id": cat.id,
            "sequence": seq_by_cat[section],
            "field_type": meta.get("type") or "char",
            "options_json": json.dumps(options, ensure_ascii=False) if options else False,
            "storage": meta.get("storage") or "json",
            "section_number": section,
            "active": True,
        }
        question = Question.search([("key", "=", key)], limit=1)
        if question:
            question.write(vals)
        else:
            question = Question.create(vals)
        questions[key] = question

    for code, sections in TEMPLATE_SECTION_MAP.items():
        meta = TEMPLATE_META[code]
        template = Template.search([("code", "=", code)], limit=1)
        vals = {
            "name": meta["name"],
            "code": code,
            "sequence": list(TEMPLATE_SECTION_MAP.keys()).index(code) * 10 + 10,
            "intro_text": "<p>%s</p>" % meta["intro"],
            "closing_text": "<p>%s</p>" % meta["closing"],
            "active": True,
        }
        if template:
            template.write(vals)
        else:
            template = Template.create(vals)

        # Rebuild lines only if empty (preserve user customizations)
        if template.line_ids:
            continue
        line_vals = []
        seq = 0
        for key, question in questions.items():
            qmeta = FORM_FIELDS.get(key) or {}
            section = qmeta.get("section")
            if section not in sections:
                continue
            seq += 10
            line_vals.append(
                {
                    "template_id": template.id,
                    "question_id": question.id,
                    "sequence": seq,
                    "required": question.storage == "column",
                    "active": True,
                    "visible": True,
                }
            )
        if line_vals:
            Line.create(line_vals)

    return True


def build_sections_from_lines(assessment, raw_values):
    """Secciones PDF/resumen a partir de líneas activas del levantamiento."""
    values = dict(raw_values or {})
    lines = assessment.question_line_ids.filtered(
        lambda l: l.active and l.visible
    ).sorted("sequence")
    by_cat = {}
    for line in lines:
        by_cat.setdefault(line.category_id, []).append(line)
    sections = []
    number = 0
    for category, cat_lines in sorted(
        by_cat.items(), key=lambda item: (item[0].sequence, item[0].id)
    ):
        if not category.active:
            continue
        number += 1
        rows = []
        for line in cat_lines:
            question = line.question_id
            key = question.key
            value = values.get(key)
            options = question.get_options_dict()
            if not is_value_filled(value) and question.field_type != "boolean":
                continue
            if key in FORM_FIELDS:
                display = format_field_value(key, value)
            elif question.field_type == "boolean":
                display = (
                    "Sí"
                    if value in (True, "true", 1, "1")
                    else ("No" if value in (False, "false", 0, "0") else "")
                )
            elif question.field_type == "multiselect":
                items = (
                    value
                    if isinstance(value, (list, tuple))
                    else ([value] if value else [])
                )
                display = ", ".join(
                    options.get(str(i), str(i)) for i in items if i not in (None, "")
                )
            elif question.field_type == "select":
                display = options.get(str(value), str(value) if value else "")
            else:
                display = "" if value in (None, False) else str(value)
            if display == "" and question.field_type != "boolean":
                continue
            rows.append(
                {
                    "key": key,
                    "label": question.name,
                    "value": display,
                    "raw": value,
                    "type": question.field_type,
                }
            )
        sections.append(
            {
                "number": number,
                "title": category.name,
                "heading": "%s. %s" % (number, category.name),
                "rows": rows,
            }
        )
    return sections
