# -*- coding: utf-8 -*-
from email.utils import parseaddr

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "justech_mail")
class TestCompanyMailIdentity(TransactionCase):
    """Four companies: From / domain / identity must match document company_id."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Company = cls.env["res.company"]
        cls.companies = {
            "justech": cls.Company.browse(1),
            "plugsafe": cls.Company.browse(2),
            "justoffice": cls.Company.browse(3),
            "omni": cls.Company.browse(4),
        }
        for key, company in cls.companies.items():
            if not company.exists():
                raise AssertionError("Missing company for %s" % key)

    def _domain_of(self, email_from):
        addr = (parseaddr(email_from or "")[1] or "").lower()
        return addr.rsplit("@", 1)[-1] if "@" in addr else ""

    def test_helper_identity_per_company(self):
        expected = {
            "justech": "justech.do",
            "plugsafe": "plugsafeservices.com",
            "justoffice": "just-offices.com",
            "omni": "solutionsomni.com",
        }
        for key, company in self.companies.items():
            identity = company._get_company_mail_identity()
            self.assertEqual(identity["company_id"], company.id)
            self.assertEqual(identity["domain"], expected[key])
            self.assertEqual(self._domain_of(identity["email_from"]), expected[key])
            self.assertEqual(identity["display_name"], company.name)
            self.assertIn(expected[key], identity["allowed_domains"])

    def test_policy_rewrites_from_by_document_company(self):
        Mail = self.env["mail.mail"].sudo()
        for key, company in self.companies.items():
            identity = company._get_company_mail_identity()
            mail = Mail.create(
                {
                    "subject": "P1 identity %s" % key,
                    "body_html": "<p>test</p>",
                    "email_from": "Wrong Brand <leak@just-offices.com>",
                    "email_to": "client@example.com",
                    "model": "res.company",
                    "res_id": company.id,
                    "record_company_id": company.id,
                    "auto_delete": False,
                }
            )
            mail._justech_apply_outgoing_policy()
            mail.invalidate_recordset()
            self.assertEqual(
                self._domain_of(mail.email_from),
                identity["domain"],
                "From domain mismatch for %s" % key,
            )
            self.assertEqual(
                (parseaddr(mail.email_from)[1] or "").lower(),
                (parseaddr(identity["email_from"])[1] or "").lower(),
            )

    def test_helpdesk_alias_constraint(self):
        Team = self.env["helpdesk.team"].sudo()
        justech = self.companies["justech"]
        justoffice_domain = self.companies["justoffice"].alias_domain_id
        team = Team.search([("company_id", "=", justech.id)], limit=1)
        if not team or not team.alias_id or not justoffice_domain:
            self.skipTest("No JUSTECH helpdesk team/alias to constrain")
        with self.assertRaises(ValidationError):
            team.alias_id.write({"alias_domain_id": justoffice_domain.id})


@tagged("post_install", "-at_install", "justech_mail")
class TestHelpdeskFourCompanies(TransactionCase):
    def test_four_company_tickets_identity(self):
        Ticket = self.env["helpdesk.ticket"].sudo()
        Team = self.env["helpdesk.team"].sudo()
        Mail = self.env["mail.mail"].sudo()
        Template = self.env["mail.template"].sudo()
        tmpl = Template.search([("model", "=", "helpdesk.ticket"), ("id", "=", 73)], limit=1)

        results = []
        for company in self.env["res.company"].browse([1, 2, 3, 4]):
            if not company.exists() or not company.alias_domain_id:
                continue
            team = Team.search([("company_id", "=", company.id)], limit=1)
            if not team:
                continue
            team._justech_align_alias_domain()
            partner = self.env["res.partner"].sudo().create(
                {
                    "name": "Mail Audit Client %s" % company.id,
                    "email": "client-co%s@example.com" % company.id,
                }
            )
            ticket = Ticket.create(
                {
                    "name": "P1 mail identity company %s" % company.id,
                    "team_id": team.id,
                    "company_id": company.id,
                    "partner_id": partner.id,
                }
            )
            identity = company._get_company_mail_identity()
            rendered_from = False
            if tmpl:
                rendered = tmpl._generate_template([ticket.id], ["email_from"])
                rendered_from = (rendered.get(ticket.id) or {}).get("email_from")
            mail = Mail.create(
                {
                    "subject": ticket.name,
                    "body_html": "<p>ticket</p>",
                    "email_from": rendered_from or team.alias_email_from or "x@example.com",
                    "email_to": partner.email,
                    "model": "helpdesk.ticket",
                    "res_id": ticket.id,
                    "record_company_id": company.id,
                    "auto_delete": False,
                }
            )
            mail._justech_apply_outgoing_policy()
            mail.invalidate_recordset()
            from_domain = (parseaddr(mail.email_from)[1] or "").rsplit("@", 1)[-1].lower()
            team_domain = (
                team.alias_id.alias_domain_id.name.lower()
                if team.alias_id and team.alias_id.alias_domain_id
                else ""
            )
            results.append(
                {
                    "company": company.name,
                    "company_id": company.id,
                    "from_domain": from_domain,
                    "expected": identity["domain"],
                    "team_domain": team_domain,
                    "email_from": mail.email_from,
                    "state": mail.state,
                }
            )
            self.assertEqual(from_domain, identity["domain"])
            self.assertEqual(team_domain, identity["domain"])
            self.assertNotEqual(mail.state, "cancel")

        self.assertGreaterEqual(len(results), 4, results)
