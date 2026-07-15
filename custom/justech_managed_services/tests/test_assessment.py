# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


@tagged("post_install", "-at_install")
class TestManagedServiceAssessment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Assessment = cls.env["justech.managed.service.assessment"]
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Cliente Test MS",
                "email": "cliente.ms@example.invalid",
                "is_company": True,
            }
        )
        cls.user_ms = cls.env["res.users"].create(
            {
                "name": "Consultor MS Test",
                "login": "consultor_ms_test",
                "email": "consultor.ms@example.invalid",
                "groups_id": [
                    (6, 0, [cls.env.ref("justech_managed_services.group_ms_user").id])
                ],
            }
        )

    def _create_assessment(self, **extra):
        vals = {
            "title": "Levantamiento test",
            "partner_id": self.partner.id,
            "consultant_id": self.user_ms.id,
        }
        vals.update(extra)
        return self.Assessment.create(vals)

    def test_create_sequence_and_token(self):
        assessment = self._create_assessment()
        self.assertTrue(assessment.name.startswith("LEV-"))
        self.assertNotEqual(assessment.name, "Nuevo")
        assessment.action_generate_link()
        self.assertTrue(assessment.access_token)
        self.assertGreaterEqual(len(assessment.access_token), 32)
        self.assertIn(assessment.access_token, assessment.public_url)

    def test_public_save_and_submit(self):
        assessment = self._create_assessment()
        assessment.action_generate_link()
        token = assessment.access_token
        result, status = assessment.sudo().public_get_by_token(token)
        self.assertEqual(status, "ok")
        save = assessment.public_save_partial(
            {"employee_count_range": "1_25", "support_users_count": 10}
        )
        self.assertEqual(assessment.state, "in_progress")
        self.assertGreater(save["completion_percent"], 0)
        self.assertTrue(assessment.date_first_activity)
        assessment.public_submit(
            {
                "acceptance_confirmed": True,
                "completed_by_name": "Tester",
                "completed_by_job": "IT Manager",
            }
        )
        self.assertEqual(assessment.state, "done")
        self.assertFalse(assessment.link_active)

    def test_block_invalid_token(self):
        assessment, status = self.Assessment.sudo().public_get_by_token("token-invalido")
        self.assertFalse(assessment)
        self.assertEqual(status, "invalid")
        assessment = self._create_assessment()
        assessment.action_generate_link()
        assessment.action_cancel()
        _, status = assessment.sudo().public_get_by_token(assessment.access_token)
        self.assertEqual(status, "cancelled")

    def test_crm_opportunity_no_duplicate(self):
        assessment = self._create_assessment()
        action1 = assessment.action_create_opportunity()
        self.assertTrue(assessment.opportunity_id)
        opp_id = assessment.opportunity_id.id
        action2 = assessment.action_create_opportunity()
        self.assertEqual(assessment.opportunity_id.id, opp_id)
        self.assertEqual(action1.get("res_id"), action2.get("res_id"))

    def test_print_sections_use_labels(self):
        assessment = self._create_assessment()
        assessment.action_generate_link()
        assessment.public_save_partial(
            {
                "org_company_name": "ACME",
                "employee_count_range": "51_100",
                "support_users_count": 75,
                "work_mode": "hibrida",
                "brands": ["dell", "hp"],
                "platforms": ["m365", "vpn"],
                "outsource_services": ["mesa_ayuda", "soporte_remoto", "otro"],
                "support_levels": ["nivel_1"],
                "coverage_schedule": "personalizado",
                "custom_schedule_comment": "Lunes a domingo 7-19",
                "service_modality": "recomendacion_justech",
                "monthly_requests_range": "51_100",
                "frequent_requests": ["passwords", "email"],
                "current_support_provider": "mixto",
                "uses_ticket_platform": True,
                "ticket_platform_name": "Jira",
                "critical_response_time": "1_hora",
                "critical_situations": ["sin_internet", "otra"],
                "other_critical_situation": "Planta fría",
                "security_items": ["politicas_seguridad"],
                "nda_required": True,
                "outsourcing_objectives": ["especialistas"],
                "expected_start": "30_dias",
                "budget_status": "alternativas",
                "approximate_budget": "RD$ 80,000",
                "final_comments": "Comentario final UAT",
            }
        )
        sections = assessment.get_form_print_sections()
        self.assertEqual(len(sections), 16)
        filled_sections = [s for s in sections if s["rows"]]
        self.assertGreaterEqual(len(filled_sections), 10)
        joined = " ".join(
            "%s %s" % (row["label"], row["value"])
            for section in sections
            for row in section["rows"]
        )
        self.assertIn("Cantidad aproximada de empleados", joined)
        self.assertIn("51 a 100", joined)
        self.assertIn("Soporte remoto", joined)
        self.assertIn("Dell", joined)
        self.assertNotIn("employee_count_range", joined)
        self.assertNotIn("soporte_remoto", joined)

    def test_unlink_restriction(self):
        assessment = self._create_assessment()
        assessment.write({"state": "done"})
        with self.assertRaises(UserError):
            assessment.with_user(self.user_ms).unlink()
        assessment.with_user(self.env.ref("base.user_admin")).unlink()
