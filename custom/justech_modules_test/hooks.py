def post_init_hook(env):
    from odoo.modules.module import load_manifest

    manifest = load_manifest("justech_modules_test")
    register_data = manifest.get("justech_register")
    if register_data:
        env["justech.license.service"].register_from_manifest(
            "justech_modules_test",
            register_data,
        )
