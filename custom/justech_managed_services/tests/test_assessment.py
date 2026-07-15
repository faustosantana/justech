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
        assessment.action_create_opportunity()
        self.assertTrue(assessment.opportunity_id)
        with self.assertRaises(UserError):
            assessment.action_create_opportunity()

    def test_unlink_restriction(self):
        assessment = self._create_assessment()
        assessment.write({"state": "done"})
        with self.assertRaises(UserError):
            assessment.with_user(self.user_ms).unlink()
        assessment.with_user(self.env.ref("base.user_admin")).unlink()
