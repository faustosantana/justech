# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
import json
import logging

from markupsafe import Markup

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class JustechAssessmentPortal(http.Controller):

    def _render_error(self, error_code, assessment=None):
        return request.render(
            "justech_managed_services.assessment_public_error",
            {
                "error_code": error_code,
                "assessment": assessment,
            },
        )

    def _get_assessment_for_token(self, token):
        return request.env["justech.managed.service.assessment"].sudo().public_get_by_token(token)

    @http.route(
        ["/servicios/levantamiento/<string:token>"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def assessment_form(self, token, **kw):
        assessment, status = self._get_assessment_for_token(token)
        if status == "invalid" or not assessment:
            return self._render_error("invalid")
        if status in ("cancelled", "inactive", "expired", "submitted"):
            return self._render_error(status, assessment=assessment)
        labels = assessment.get_form_labels_payload()
        values = {
            "assessment": assessment,
            "partner_name": assessment.partner_id.display_name,
            "form_values": assessment.get_form_display_values(),
            "form_values_json": Markup(
                json.dumps(assessment.get_form_display_values(), ensure_ascii=False)
            ),
            "field_labels_json": Markup(
                json.dumps(labels.get("field_labels") or {}, ensure_ascii=False)
            ),
            "option_labels_json": Markup(
                json.dumps(labels.get("option_labels") or {}, ensure_ascii=False)
            ),
            "tracked_keys_json": Markup(
                json.dumps(labels.get("tracked_keys") or [], ensure_ascii=False)
            ),
            "completion_percent": assessment.completion_percent or 0,
            "readonly": False,
        }
        return request.render(
            "justech_managed_services.assessment_public_form",
            values,
        )

    @http.route(
        ["/servicios/levantamiento/<string:token>/save"],
        type="json",
        auth="public",
        website=True,
        csrf=False,
    )
    def assessment_save(self, token, form_data=None, **kw):
        assessment, status = self._get_assessment_for_token(token)
        if status != "ok" or not assessment:
            return {"error": status or "invalid"}
        try:
            result = assessment.public_save_partial(form_data or {})
            return {"ok": True, **result}
        except ValidationError as exc:
            return {"error": "validation", "message": str(exc)}
        except Exception:
            _logger.exception("Error guardando levantamiento público")
            return {"error": "server"}

    @http.route(
        ["/servicios/levantamiento/<string:token>/submit"],
        type="json",
        auth="public",
        website=True,
        csrf=False,
    )
    def assessment_submit(self, token, form_data=None, **kw):
        assessment, status = self._get_assessment_for_token(token)
        if status != "ok" or not assessment:
            return {"error": status or "invalid"}
        try:
            payload = dict(form_data or {})
            result = assessment.public_submit(payload)
            return {"ok": True, **result}
        except ValidationError as exc:
            return {"error": "validation", "message": str(exc)}
        except Exception:
            _logger.exception("Error enviando levantamiento público")
            return {"error": "server"}
