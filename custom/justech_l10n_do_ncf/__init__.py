from . import models
from . import services
from . import wizards


def post_init_hook(env):
    env["justech.do.purchase.emission.config"].ensure_configs_for_companies()
