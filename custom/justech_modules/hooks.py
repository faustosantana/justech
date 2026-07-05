def post_init_hook(env):
    env["justech.license.service"].register_platform_seed()
