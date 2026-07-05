def pre_init_hook(cr_or_env):
    """Cleanup duplicates and migrate legacy license_key before constraints apply."""
    cr = getattr(cr_or_env, "cr", cr_or_env)
    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'justech_license_company'
        )
        """
    )
    if not cr.fetchone()[0]:
        return
    cr.execute(
        """
        DELETE FROM justech_license_company a
        USING justech_license_company b
        WHERE a.id > b.id
          AND a.license_id = b.license_id
          AND a.company_id = b.company_id
        """
    )
    cr.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'justech_license' AND column_name = 'license_key'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'justech_license' AND column_name = 'license_key_hash'
        """
    )
    if not cr.fetchone():
        return
    # Hash migration deferred to post_init (needs env for pepper); column prep only here.


def post_init_hook(env):
    env["justech.license"].migrate_plaintext_license_keys()
    env["justech.license"].backfill_missing_license_hashes()
    env["justech.license.service"].register_platform_seed()
    from .hooks_register import register_all_installed_manifests

    register_all_installed_manifests(env)
