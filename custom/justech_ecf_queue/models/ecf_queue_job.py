import uuid
from datetime import timedelta

from odoo import api, fields, models, _


class JustechEcfQueueJob(models.Model):
    _name = "justech.ecf.queue.job"
    _description = "Cola de envío e-CF"
    _order = "priority desc, id asc"

    name = fields.Char(required=True, default=lambda s: "JOB-%s" % uuid.uuid4().hex[:8].upper())
    company_id = fields.Many2one("res.company", required=True, index=True)
    document_id = fields.Many2one("justech.ecf.document", required=True, index=True, ondelete="restrict")
    state = fields.Selection(
        selection=[
            ("pending", "Pendiente"),
            ("running", "En ejecución"),
            ("done", "Hecho"),
            ("failed", "Fallido"),
            ("dead", "Dead-letter"),
            ("cancelled", "Cancelado"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    priority = fields.Integer(default=10, index=True)
    attempt = fields.Integer(default=0)
    max_attempts = fields.Integer(default=5)
    idempotency_key = fields.Char(required=True, index=True)
    locked_by = fields.Char()
    locked_until = fields.Datetime()
    next_run_at = fields.Datetime(default=fields.Datetime.now, index=True)
    last_error = fields.Text()

    _sql_constraints = [
        ("idempotency_uniq", "unique(company_id, idempotency_key)", "Idempotencia duplicada en cola."),
    ]

    @api.model
    def create_for_document(self, document):
        document.ensure_one()
        key = document.idempotency_key or "ecf-%s-%s" % (document.company_id.id, document.id)
        if not document.idempotency_key:
            document.idempotency_key = key
        existing = self.search(
            [("company_id", "=", document.company_id.id), ("idempotency_key", "=", key), ("state", "in", ["pending", "running"])],
            limit=1,
        )
        if existing:
            return existing
        return self.create(
            {
                "company_id": document.company_id.id,
                "document_id": document.id,
                "idempotency_key": key,
            }
        )

    def _backoff_minutes(self):
        self.ensure_one()
        return min(2 ** max(self.attempt, 1), 60)

    @api.model
    def cron_process_queue(self, limit=50):
        now = fields.Datetime.now()
        jobs = self.search(
            [("state", "=", "pending"), ("next_run_at", "<=", now)],
            order="priority desc, id asc",
            limit=limit,
        )
        for job in jobs:
            job._process()
        return True

    def _process(self):
        self.ensure_one()
        self.write({"state": "running", "locked_by": "cron", "locked_until": fields.Datetime.now() + timedelta(minutes=5)})
        doc = self.document_id
        try:
            self.env["justech.ecf.dgii.client"].send_ecf(doc)
            self.write({"state": "done", "locked_by": False, "locked_until": False})
        except Exception as exc:
            attempt = self.attempt + 1
            vals = {"attempt": attempt, "last_error": str(exc)[:2000], "locked_by": False, "locked_until": False}
            if attempt >= self.max_attempts:
                vals["state"] = "dead"
                doc.write({"state": "failed"})
                doc._log_event("queue_dead", result="error", message=str(exc)[:500])
            else:
                vals.update(
                    {
                        "state": "pending",
                        "next_run_at": fields.Datetime.now() + timedelta(minutes=self._backoff_minutes()),
                    }
                )
                doc.write({"state": "retry", "contingency": True})
                doc._log_event("queue_retry", result="warn", message=str(exc)[:500], attempt=attempt)
            self.write(vals)
