"""Public governance exceptions."""

from odoo.exceptions import UserError


class HelleniaGovernanceError(UserError):
    """Raised when governance rules block an operation."""
