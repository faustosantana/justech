from . import models
from . import wizard


def post_init_hook(env):
    env["res.company"].search([]).write({"hellenia_show_qr_on_invoice": False})
