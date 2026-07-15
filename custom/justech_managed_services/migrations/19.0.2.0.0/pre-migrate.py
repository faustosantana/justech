# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
"""Migrar estados de levantamiento Fase 1 → Fase 2."""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE justech_managed_service_assessment
           SET state = CASE state
               WHEN 'reviewed' THEN 'review'
               WHEN 'proposal_ready' THEN 'approved_proposal'
               ELSE state
           END
         WHERE state IN ('reviewed', 'proposal_ready')
        """
    )
