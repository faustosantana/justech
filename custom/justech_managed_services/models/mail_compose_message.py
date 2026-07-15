# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def _action_send_mail(self, auto_commit=False):
        result_mails_su, result_messages = super()._action_send_mail(
            auto_commit=auto_commit
        )
        if not self.env.context.get("justech_assessment_mark_email_sent"):
            return result_mails_su, result_messages

        assessment_ids = self.env.context.get("justech_assessment_id")
        assessments = self.env["justech.managed.service.assessment"]
        if assessment_ids:
            assessments = assessments.browse(assessment_ids).exists()
        else:
            for wizard in self:
                if wizard.model != "justech.managed.service.assessment":
                    continue
                res_ids = wizard._evaluate_res_ids() if wizard.model else []
                assessments |= assessments.browse(res_ids)

        for assessment in assessments:
            recipient = assessment.email
            subject = assessment.invite_subject
            for wizard in self:
                if wizard.subject:
                    subject = wizard.subject
                if wizard.partner_ids:
                    recipient = (
                        wizard.partner_ids[:1].email or recipient
                    )
            mail_state = "sent"
            if result_mails_su:
                mail_state = result_mails_su[:1].state or "sent"
            assessment.action_mark_email_sent(
                recipient=recipient,
                subject=subject,
                mail_state=mail_state,
            )
        return result_mails_su, result_messages
