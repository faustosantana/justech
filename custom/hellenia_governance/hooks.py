def post_init_hook(env):
    env["hellenia.governance.service"]._seed_default_policies()
