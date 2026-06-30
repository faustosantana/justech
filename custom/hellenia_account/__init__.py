# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)

from . import models


def post_init_hook(env):
    """Configura bancos y métodos tras instalar el módulo (idempotente)."""
    setup = env["hellenia.account.payment.setup"]
    setup.configure_banks_and_payments()
    setup.configure_withholding_reference()
