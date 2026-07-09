#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Valida archivos físicos de ir_attachment (assets y filestore) — read-only."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _default_filestore(env):
    from odoo.tools import config

    dbname = env.cr.dbname
    return os.path.join(config["data_dir"], "filestore", dbname)


def validate(env, filestore_root=None, label="live"):
    cr = env.cr
    dbname = cr.dbname
    if filestore_root is None:
        filestore_root = _default_filestore(env)

    errors = []
    checks = {}

    cr.execute(
        """
        SELECT COUNT(*) FROM ir_attachment
        WHERE store_fname IS NOT NULL AND store_fname != ''
        """
    )
    checks["attachments_with_store_fname"] = cr.fetchone()[0]

    cr.execute(
        """
        SELECT id, name, store_fname, url
        FROM ir_attachment
        WHERE url LIKE '/web/assets/%%'
          AND store_fname IS NOT NULL AND store_fname != ''
        ORDER BY write_date DESC
        """
    )
    asset_rows = cr.fetchall()
    checks["asset_attachments"] = len(asset_rows)

    missing_assets = []
    for att_id, name, store_fname, url in asset_rows:
        path = os.path.join(filestore_root, store_fname)
        if not os.path.isfile(path):
            missing_assets.append(
                {"id": att_id, "name": name, "store_fname": store_fname, "url": url}
            )

    checks["missing_asset_files"] = len(missing_assets)
    checks["filestore_root"] = filestore_root

    if missing_assets:
        errors.append(f"missing_asset_files={len(missing_assets)}")
        checks["missing_asset_sample"] = missing_assets[:10]

    # Muestra de attachments no-asset (PDFs, imágenes) — tolerancia 0 en assets, sample en otros
    cr.execute(
        """
        SELECT store_fname FROM ir_attachment
        WHERE store_fname IS NOT NULL AND store_fname != ''
          AND (url IS NULL OR url NOT LIKE '/web/assets/%%')
        ORDER BY id DESC
        LIMIT 50
        """
    )
    sample_missing = 0
    for (store_fname,) in cr.fetchall():
        if not os.path.isfile(os.path.join(filestore_root, store_fname)):
            sample_missing += 1
    checks["non_asset_sample_missing"] = sample_missing
    checks["non_asset_sample_size"] = 50

    ok = len(errors) == 0
    return {
        "label": label,
        "ts": utc_now(),
        "database": dbname,
        "ok": ok,
        "errors": errors,
        "checks": checks,
    }
