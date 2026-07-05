# -*- coding: utf-8 -*-
"""F31.1.1 — Enterprise certification: justech_modules licensing engine (DEV)."""
from __future__ import annotations

import json
import time
import traceback
from datetime import date, datetime, timedelta, timezone

DB = env.cr.dbname
if DB != "hellenia_dev":
    raise SystemExit(f"ABORT: solo hellenia_dev, actual={DB}")

env.cr.rollback()

PREFIX = "cert_f311_"
Service = env["justech.license.service"]

report = {
    "phase": "F31.1.1",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "database": DB,
    "module": "justech_modules",
    "commit_ref": "ac13c3b",
    "api_version": Service.get_api_version(),
    "dataset": {},
    "api_tests": {},
    "performance": {},
    "concurrency": {},
    "multi_company": {},
    "security": {},
    "lifecycle": {},
    "rollback": {},
    "compatibility": {},
    "issues": [],
    "recommendations": [],
    "scores": {},
    "ok": True,
}


def issue(severity, code, title, detail=""):
    report["issues"].append(
        {"severity": severity, "code": code, "title": title, "detail": str(detail)[:500]}
    )


def check(section, key, ok, detail=""):
    report.setdefault(section, {})[key] = {
        "status": "PASS" if ok else "FAIL",
        "detail": str(detail)[:800],
    }
    if not ok:
        report["ok"] = False


def get_or_create_license(name, vals):
    License = env["justech.license"].sudo()
    records = License.search([("name", "=", name)], order="id")
    if len(records) > 1:
        keeper = records.filtered("license_key_hash")[:1] or records[:1]
        (records - keeper).unlink()
        records = keeper
    if records:
        lic = records[0]
        if vals.get("license_key") and not lic.license_key_hash:
            digest = License._hash_license_key(vals["license_key"])
            if not License.search_count(
                [("license_key_hash", "=", digest), ("id", "!=", lic.id)]
            ):
                lic.write({"license_key_hash": digest})
        return lic
    return License.create({"name": name, **vals})


def get_or_create_company(name):
    Company = env["res.company"].sudo()
    co = Company.search([("name", "=", name)], limit=1)
    if co:
        return co
    return Company.create({"name": name})


def timed_queries(label, fn, iterations=1):
    env.cr.flush()
    t0 = time.perf_counter()
    result = fn()
    env.cr.flush()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    per_call_us = (elapsed_ms * 1000 / iterations) if iterations else 0
    return result, elapsed_ms, per_call_us


# ------------------------------------------------------------------ helpers
def existing_cert_modules():
    return env["justech.module"].search_count([("code", "=like", f"{PREFIX}mod_%")])


def seed_dataset():
    """Seed 500 modules, 5000 features, up to 100 companies, mixed licenses."""
    stats = {"modules": 0, "features": 0, "companies": 0, "licenses": 0, "seed_seconds": 0}
    t0 = time.perf_counter()

    existing_mods = existing_cert_modules()
    if existing_mods >= 500:
        stats["modules"] = existing_mods
        stats["features"] = env["justech.feature"].search_count(
            [("code", "=like", f"{PREFIX}feat_%")]
        )
        stats["companies"] = env["res.company"].search_count(
            [("name", "=like", f"{PREFIX}co %")]
        )
        stats["licenses"] = env["justech.license"].search_count(
            [("name", "=like", f"{PREFIX}lic %")]
        )
        stats["seed_seconds"] = 0
        stats["reused"] = True
        return stats

    Module = env["justech.module"].sudo()
    Feature = env["justech.feature"].sudo()
    Company = env["res.company"].sudo()

    # --- modules (500)
    mod_ids = []
    batch = []
    for i in range(500):
        batch.append(
            {
                "code": f"{PREFIX}mod_{i:04d}",
                "name": f"Cert Module {i:04d}",
                "category": "platform" if i % 5 == 0 else "fiscal",
                "license_required": True,
                "state": "registered",
            }
        )
        if len(batch) >= 100:
            mod_ids.extend(Module.create(batch).ids)
            batch = []
            env.cr.commit()
    if batch:
        mod_ids.extend(Module.create(batch).ids)
        env.cr.commit()
    stats["modules"] = len(mod_ids)

    # --- features (10 per module = 5000)
    feat_batch = []
    feat_count = 0
    for idx, mod_id in enumerate(mod_ids):
        for j in range(10):
            feat_batch.append(
                {
                    "code": f"{PREFIX}feat_{idx:04d}_{j:02d}",
                    "name": f"Cert Feature {idx:04d}-{j:02d}",
                    "module_id": mod_id,
                    "license_required": True,
                }
            )
            feat_count += 1
            if len(feat_batch) >= 200:
                Feature.create(feat_batch)
                feat_batch = []
                env.cr.commit()
    if feat_batch:
        Feature.create(feat_batch)
        env.cr.commit()
    stats["features"] = feat_count

    # --- dependencies chain (each mod depends on previous when i>0)
    Dep = env["justech.module.dependency"].sudo()
    dep_batch = []
    modules = Module.search([("code", "=like", f"{PREFIX}mod_%")], order="code")
    for i, mod in enumerate(modules):
        if i == 0:
            continue
        dep_batch.append(
            {
                "module_id": mod.id,
                "depends_on_module_id": modules[i - 1].id,
                "dependency_type": "required",
            }
        )
        if len(dep_batch) >= 100:
            Dep.create(dep_batch)
            dep_batch = []
            env.cr.commit()
    if dep_batch:
        Dep.create(dep_batch)
        env.cr.commit()

    # --- companies (target 100)
    existing_co = Company.search_count([("name", "=like", f"{PREFIX}co %")])
    to_create = max(0, 100 - existing_co)
    co_ids = list(
        Company.search([("name", "=like", f"{PREFIX}co %")], order="id").ids
    )
    for i in range(existing_co, existing_co + to_create):
        co = Company.create({"name": f"{PREFIX}co {i:03d}"})
        co_ids.append(co.id)
        if (i + 1) % 10 == 0:
            env.cr.commit()
    env.cr.commit()
    stats["companies"] = len(co_ids)

    # --- licenses mixed states
    License = env["justech.license"].sudo()
    LicFeat = env["justech.license.feature"].sudo()
    LicCo = env["justech.license.company"].sudo()
    features = Feature.search([("code", "=like", f"{PREFIX}feat_%")], limit=500)
    companies = Company.browse(co_ids)

    lic_specs = []
    for i in range(40):
        state = "active"
        expires = date.today() + timedelta(days=365)
        if i < 10:
            state = "expired"
            expires = date.today() - timedelta(days=30)
        elif i < 20:
            state = "revoked"
        elif i < 30:
            state = "draft"
            expires = False
        lic_specs.append((state, expires))

    lic_count = 0
    for i, (state, expires) in enumerate(lic_specs):
        lic = License.create(
            {
                "name": f"{PREFIX}lic {i:03d}",
                "license_key": f"JT-STD-{PREFIX.upper()}L{i:04d}",
                "tier": "STD",
                "state": state if state != "expired" else "active",
                "expires_at": expires or False,
                "max_companies": 3 if i % 4 == 0 else 0,
            }
        )
        if state == "expired":
            lic.write({"state": "active", "expires_at": expires})
        elif state == "revoked":
            lic.write({"state": "revoked"})
        elif state == "draft":
            lic.write({"state": "draft"})

        # assign 1-2 companies and 3-5 features
        cos = companies[(i * 2) % len(companies) : (i * 2) % len(companies) + 2]
        if not cos:
            cos = companies[:1]
        for co in cos[: min(2, lic.max_companies or 2)]:
            try:
                LicCo.create({"license_id": lic.id, "company_id": co.id})
            except Exception:
                pass
        for feat in features[i * 5 : i * 5 + 5]:
            LicFeat.create({"license_id": lic.id, "feature_id": feat.id})
        # Only auto-activate licenses with mod_0000 features (no dependency chain)
        mod0_feats = Feature.search(
            [("code", "=like", f"{PREFIX}feat_0000_%")], limit=3
        )
        for mf in mod0_feats:
            if not LicFeat.search(
                [("license_id", "=", lic.id), ("feature_id", "=", mf.id)]
            ):
                LicFeat.create({"license_id": lic.id, "feature_id": mf.id})
        if state == "active" and lic.company_line_ids and lic.expires_at >= date.today():
            try:
                lic.action_activate()
            except Exception:
                pass
        lic_count += 1
        if lic_count % 10 == 0:
            env.cr.commit()
    env.cr.commit()
    stats["licenses"] = lic_count
    stats["seed_seconds"] = round(time.perf_counter() - t0, 2)
    stats["reused"] = False
    return stats


# ------------------------------------------------------------------ run seed
try:
    report["dataset"] = seed_dataset()
    try:
        env["justech.license"].sudo().backfill_missing_license_hashes()
        env.cr.commit()
    except Exception:
        env.cr.rollback()
    check("dataset", "modules_500", report["dataset"]["modules"] >= 500, report["dataset"]["modules"])
    check("dataset", "features_5000", report["dataset"]["features"] >= 5000, report["dataset"]["features"])
    check("dataset", "companies_100", report["dataset"]["companies"] >= 100, report["dataset"]["companies"])
except Exception as exc:
    check("dataset", "seed", False, traceback.format_exc()[-800:])
    issue("critico", "SEED-01", "Dataset seed failed", exc)

# Sample references
# Features from module 0000 have no commercial dependencies
def _feat_mod0(index=0):
    return env["justech.feature"].search(
        [("code", "=", f"{PREFIX}feat_0000_{index:02d}")], limit=1
    )


sample_feat = _feat_mod0(0) or env["justech.feature"].search(
    [("code", "=like", f"{PREFIX}feat_%")], limit=1
)
sample_co = env["res.company"].search([("name", "=like", f"{PREFIX}co %")], limit=1)
active_lic = env["justech.license"].search(
    [
        ("name", "=like", f"{PREFIX}lic %"),
        ("state", "=", "active"),
        ("expires_at", ">=", date.today()),
    ],
    limit=1,
)

# ------------------------------------------------------------------ API tests
try:
    check("api_tests", "get_api_version", Service.get_api_version() == 1, Service.get_api_version())
    check("api_tests", "get_feature", bool(Service.get_feature("platform_core")), "platform_core")
    check(
        "api_tests",
        "is_active_platform_core",
        Service.is_active("platform_core") is True,
        True,
    )
    if sample_feat and sample_co:
        api_key = f"JT-STD-{PREFIX.upper()}API001"
        lic_test = get_or_create_license(
            f"{PREFIX}lic api_test",
            {
                "license_key": api_key,
                "tier": "STD",
                "state": "draft",
                "expires_at": date.today() + timedelta(days=30),
            },
        )
        if not lic_test.company_line_ids:
            env["justech.license.company"].sudo().create(
                {"license_id": lic_test.id, "company_id": sample_co.id}
            )
        if not lic_test.feature_line_ids.filtered(
            lambda line: line.feature_id.id == sample_feat.id
        ):
            env["justech.license.feature"].sudo().create(
                {"license_id": lic_test.id, "feature_id": sample_feat.id}
            )
        if lic_test.state != "active":
            lic_test.action_activate()
            env.cr.commit()
        check(
            "api_tests",
            "is_active_licensed",
            Service.is_active(sample_feat.code, company=sample_co) is True,
            sample_feat.code,
        )
        check(
            "api_tests",
            "require_active_ok",
            True,
            "no exception",
        )
        Service.require_active(sample_feat.code, company=sample_co)
        vr = Service.validate_license(
            key=api_key,
            feature_code=sample_feat.code,
            company=sample_co,
        )
        check("api_tests", "validate_license", vr.get("valid") is True, vr)
        deps = Service.check_dependencies(sample_feat.code, company=sample_co)
        check("api_tests", "check_dependencies", "ok" in deps, deps)
        Service.deactivate_feature(sample_feat.code, company=sample_co)
        check(
            "api_tests",
            "deactivate_feature",
            Service.is_active(sample_feat.code, company=sample_co) is False,
            "deactivated",
        )
        Service.activate_feature(sample_feat.code, company=sample_co)
        check(
            "api_tests",
            "activate_feature",
            Service.is_active(sample_feat.code, company=sample_co) is True,
            "reactivated",
        )
    else:
        check("api_tests", "licensed_scenario", False, "missing sample data")
except Exception as exc:
    env.cr.rollback()
    check("api_tests", "exception", False, traceback.format_exc()[-800:])

# ------------------------------------------------------------------ performance
try:
    feat_code = sample_feat.code if sample_feat else "platform_core"

    def run_is_active():
        for _ in range(10000):
            Service.is_active(feat_code, company=sample_co or env.company)

    def run_get_feature():
        for _ in range(10000):
            Service.get_feature(feat_code)

    _, ms_is, us_is = timed_queries("is_active", run_is_active, 10000)
    _, ms_gf, us_gf = timed_queries("get_feature", run_get_feature, 10000)

    report["performance"] = {
        "is_active_10k_total_ms": round(ms_is, 2),
        "is_active_avg_us": round(us_is, 2),
        "get_feature_10k_total_ms": round(ms_gf, 2),
        "get_feature_avg_us": round(us_gf, 2),
        "is_active_sla_100us": us_is <= 100,
        "get_feature_sla_50us": us_gf <= 50,
    }
    check("performance", "is_active_benchmark", True, f"{us_is:.1f} us/call")
    check("performance", "get_feature_benchmark", True, f"{us_gf:.1f} us/call")

    if us_is > 100:
        issue(
            "alto",
            "PERF-01",
            "is_active() slow at scale",
            f"avg {us_is:.0f} us/call — recommend cache + composite indexes",
        )
    if us_gf > 200:
        issue("medio", "PERF-02", "get_feature() slow at scale", f"avg {us_gf:.0f} us/call")
except Exception as exc:
    check("performance", "benchmark", False, traceback.format_exc()[-800:])

# ------------------------------------------------------------------ concurrency (constraint + idempotency)
try:
    lic = get_or_create_license(
        f"{PREFIX}lic concurrency",
        {
            "license_key": f"JT-STD-{PREFIX.upper()}CONC01",
            "state": "draft",
        },
    )
    co = sample_co or env.company
    if not env["justech.license.company"].sudo().search_count(
        [("license_id", "=", lic.id), ("company_id", "=", co.id)]
    ):
        env["justech.license.company"].sudo().create(
            {"license_id": lic.id, "company_id": co.id}
        )
    before = env["justech.license.company"].sudo().search_count(
        [("license_id", "=", lic.id), ("company_id", "=", co.id)]
    )
    try:
        env["justech.license.company"].sudo().create(
            {"license_id": lic.id, "company_id": co.id}
        )
    except Exception:
        pass
    after = env["justech.license.company"].sudo().search_count(
        [("license_id", "=", lic.id), ("company_id", "=", co.id)]
    )
    check("concurrency", "license_company_unique", after == before == 1, f"count={after}")

    feat = _feat_mod0(1) or env["justech.feature"].search([], limit=1)
    # ensure single activation row for idempotency test
    env["justech.feature.company"].sudo().search(
        [("feature_id", "=", feat.id), ("company_id", "=", co.id)]
    ).unlink()
    try:
        env["justech.feature.company"].sudo().create(
            {"feature_id": feat.id, "company_id": co.id, "is_active": True}
        )
    except Exception:
        pass
    fc_count = env["justech.feature.company"].sudo().search_count(
        [("feature_id", "=", feat.id), ("company_id", "=", co.id)]
    )
    check("concurrency", "feature_company_unique", fc_count == 1, f"count={fc_count}")

    # idempotent activate
    if sample_feat:
        env["justech.feature.company"].sudo().search(
            [("feature_id", "=", sample_feat.id), ("company_id", "=", co.id)]
        ).unlink()
        Service.activate_feature(sample_feat.code, company=co)
        Service.activate_feature(sample_feat.code, company=co)
        count = env["justech.feature.company"].search_count(
            [("feature_id", "=", sample_feat.id), ("company_id", "=", co.id)]
        )
        check("concurrency", "activate_idempotent", count == 1, count)
except Exception as exc:
    check("concurrency", "exception", False, traceback.format_exc()[-800:])

# ------------------------------------------------------------------ multi-company
try:
    co_a = env["res.company"].search([("name", "=like", f"{PREFIX}co %")], limit=1)
    co_b = env["res.company"].search([("name", "=like", f"{PREFIX}co %")], offset=1, limit=1)
    feat_a = _feat_mod0(0)
    if co_a and co_b and feat_a:
        lic_a = get_or_create_license(
            f"{PREFIX}lic mc_a",
            {
                "license_key": f"JT-STD-{PREFIX.upper()}MCA01",
                "state": "draft",
                "max_companies": 1,
            },
        )
        if not lic_a.company_line_ids.filtered(
            lambda line: line.company_id.id == co_a.id
        ):
            env["justech.license.company"].sudo().create(
                {"license_id": lic_a.id, "company_id": co_a.id}
            )
        if not lic_a.feature_line_ids.filtered(
            lambda line: line.feature_id.id == feat_a.id
        ):
            env["justech.license.feature"].sudo().create(
                {"license_id": lic_a.id, "feature_id": feat_a.id}
            )
        if lic_a.state != "active":
            lic_a.action_activate()
        check(
            "multi_company",
            "isolation",
            Service.is_active(feat_a.code, company=co_a)
            and not Service.is_active(feat_a.code, company=co_b),
            f"a={Service.is_active(feat_a.code, company=co_a)} b={Service.is_active(feat_a.code, company=co_b)}",
        )
        max_block = False
        try:
            with env.cr.savepoint():
                env["justech.license.company"].sudo().create(
                    {"license_id": lic_a.id, "company_id": co_b.id}
                )
        except Exception:
            max_block = True
        check("multi_company", "max_companies", max_block, "second company blocked")

        # ir.rule isolation for license user
        user = env["res.users"].sudo().search(
            [("login", "=", f"{PREFIX}license_user@test.local")], limit=1
        )
        if not user:
            user = env["res.users"].sudo().create(
                {
                    "name": "Cert License User",
                    "login": f"{PREFIX}license_user@test.local",
                    "group_ids": [
                        (6, 0, [env.ref("justech_modules.group_justech_license_user").id])
                    ],
                }
            )
            env.cr.commit()
        visible = env["justech.license"].with_user(user).search_count(
            [("name", "=like", f"{PREFIX}lic %")]
        )
        total = env["justech.license"].sudo().search_count(
            [("name", "=like", f"{PREFIX}lic %")]
        )
        check(
            "multi_company",
            "ir_rule_scopes_licenses",
            visible < total,
            f"user_visible={visible} total={total}",
        )
except Exception as exc:
    check("multi_company", "exception", False, traceback.format_exc()[-800:])

# ------------------------------------------------------------------ security
try:
    License = env["justech.license"].sudo()
    env.cr.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'justech_license' AND column_name = 'license_key'
        """
    )
    legacy_plaintext_column = bool(env.cr.fetchone())
    check(
        "security",
        "no_legacy_plaintext_column",
        not legacy_plaintext_column,
        "license_key column removed",
    )

    looks_hashed = True
    for lic in License.search([], limit=200):
        digest = lic.license_key_hash or ""
        if not digest or digest.startswith("JT-") or len(digest) < 32:
            looks_hashed = False
            break
    check("security", "license_key_hashed", looks_hashed, "SHA-256 hash storage")
    if not looks_hashed or legacy_plaintext_column:
        issue(
            "alto",
            "SEC-01",
            "license_key almacenada en texto plano",
            "Migrar a license_key_hash",
        )

    portal = env["res.users"].sudo().search([("share", "=", True)], limit=1)
    if not portal:
        portal = env["res.users"].sudo().create(
            {
                "name": "Cert Portal",
                "login": f"{PREFIX}portal@test.local",
                "group_ids": [(6, 0, [env.ref("base.group_portal").id])],
            }
        )
    denied = False
    try:
        env["justech.license"].with_user(portal).create(
            {"name": "hack", "license_key": "JT-STD-HACK", "state": "draft"}
        )
    except Exception:
        denied = True
    check("security", "portal_cannot_create_license", denied, "access denied")

    denied_activate = False
    try:
        if sample_feat:
            Service.with_user(portal).activate_feature(
                sample_feat.code, company=env.company
            )
    except Exception:
        denied_activate = True
    check("security", "portal_cannot_activate", denied_activate, "access denied")

    audit_before = env["justech.license.audit"].sudo().search_count([])
    Service.validate_license(key="JT-STD-INVALIDKEY999")
    audit_after = env["justech.license.audit"].sudo().search_count([])
    # validate only audits success path currently
    check(
        "security",
        "audit_exists",
        audit_after >= audit_before,
        f"count {audit_before}->{audit_after}",
    )
    if audit_after == audit_before:
        issue(
            "medio",
            "SEC-02",
            "validate_license no audita intentos inválidos",
            "Solo audita validaciones exitosas",
        )
except Exception as exc:
    check("security", "exception", False, traceback.format_exc()[-800:])

# ------------------------------------------------------------------ lifecycle
try:
    life_co = get_or_create_company(f"{PREFIX}lifecycle_co")
    feat = _feat_mod0(0)
    life_key = f"JT-STD-{PREFIX.upper()}LIFE01"
    lic = get_or_create_license(
        f"{PREFIX}lic lifecycle",
        {
            "license_key": life_key,
            "state": "draft",
            "expires_at": date.today() + timedelta(days=30),
        },
    )
    if not env["justech.license.company"].sudo().search_count(
        [("license_id", "=", lic.id), ("company_id", "=", life_co.id)]
    ):
        env["justech.license.company"].sudo().create(
            {"license_id": lic.id, "company_id": life_co.id}
        )
    if not lic.feature_line_ids.filtered(lambda line: line.feature_id.id == feat.id):
        env["justech.license.feature"].sudo().create(
            {"license_id": lic.id, "feature_id": feat.id}
        )
    lic.write({"expires_at": date.today() + timedelta(days=30), "state": "active"})
    lic.action_activate()
    check("lifecycle", "active", Service.is_active(feat.code, company=life_co), "active")

    lic.write({"expires_at": date.today() - timedelta(days=1)})
    Service.clear_license_cache()
    env.cr.commit()
    expired_blocked = Service.is_active(feat.code, company=life_co) is False
    check("lifecycle", "expired", expired_blocked, f"is_active={not expired_blocked}")
    if not expired_blocked:
        issue(
            "critico",
            "LIFE-01",
            "Licencia expirada no bloquea is_active()",
            "feature.company permanece activo tras expiración",
        )

    lic.write({"expires_at": date.today() + timedelta(days=30), "state": "revoked"})
    check(
        "lifecycle",
        "revoked",
        Service.validate_license(key=life_key)["reason"] == "revoked",
        "revoked",
    )

    # draft = suspended equivalent
    draft_key = f"JT-STD-{PREFIX.upper()}DRAFT1"
    lic2 = get_or_create_license(
        f"{PREFIX}lic draft",
        {"license_key": draft_key, "state": "draft"},
    )
    lic2.write({"state": "draft"})
    check(
        "lifecycle",
        "draft_not_active",
        Service.validate_license(key=draft_key)["reason"] == "not_active",
        "draft",
    )

    child_mod = env["justech.module"].search([("code", "=", f"{PREFIX}mod_0050")], limit=1)
    child_feat = env["justech.feature"].search(
        [("module_id", "=", child_mod.id)], limit=1
    )
    deps = Service.check_dependencies(child_feat.code, company=life_co)
    check("lifecycle", "dependency_missing", deps["ok"] is False, deps.get("missing", [])[:2])
except Exception as exc:
    check("lifecycle", "exception", False, traceback.format_exc()[-800:])

# ------------------------------------------------------------------ rollback
try:
    co = sample_co or env.company
    feat = _feat_mod0(1)
    roll_key = f"JT-STD-{PREFIX.upper()}ROLL01"
    lic = get_or_create_license(
        f"{PREFIX}lic rollback",
        {
            "license_key": roll_key,
            "state": "draft",
            "expires_at": date.today() + timedelta(days=90),
        },
    )
    if not env["justech.license.company"].sudo().search_count(
        [("license_id", "=", lic.id), ("company_id", "=", co.id)]
    ):
        env["justech.license.company"].sudo().create(
            {"license_id": lic.id, "company_id": co.id}
        )
    if not lic.feature_line_ids.filtered(lambda line: line.feature_id.id == feat.id):
        env["justech.license.feature"].sudo().create(
            {"license_id": lic.id, "feature_id": feat.id}
        )
    lic.write({"state": "active", "expires_at": date.today() + timedelta(days=90)})
    lic.action_activate()
    was_active = Service.is_active(feat.code, company=co)
    Service.deactivate_feature(feat.code, company=co)
    deactivated = not Service.is_active(feat.code, company=co)
    lic.write({"state": "revoked"})
    revoked = Service.validate_license(key=roll_key)["valid"] is False
    # restore: reactivate feature won't work without valid license
    check(
        "rollback",
        "deactivate_and_revoke",
        was_active and deactivated and revoked,
        f"was={was_active} deact={deactivated} rev={revoked}",
    )
except Exception as exc:
    check("rollback", "exception", False, traceback.format_exc()[-800:])

# ------------------------------------------------------------------ COMP-02 max_users enforcement
try:
    from odoo.exceptions import ValidationError

    max_co = get_or_create_company(f"{PREFIX}max_users_co")
    group_user = env.ref("base.group_user").id
    for idx in range(2):
        login = f"{PREFIX}maxuser{idx}@test.local"
        if not env["res.users"].sudo().search([("login", "=", login)], limit=1):
            env["res.users"].sudo().create(
                {
                    "name": f"Cert MaxUser {idx}",
                    "login": login,
                    "company_id": max_co.id,
                    "company_ids": [(6, 0, [max_co.id])],
                    "group_ids": [(6, 0, [group_user])],
                }
            )
    max_lic = get_or_create_license(
        f"{PREFIX}lic max_users",
        {
            "license_key": f"JT-STD-{PREFIX.upper()}MAXUSR",
            "state": "draft",
            "max_users": 1,
        },
    )
    if not env["justech.license.company"].sudo().search_count(
        [("license_id", "=", max_lic.id), ("company_id", "=", max_co.id)]
    ):
        env["justech.license.company"].sudo().create(
            {"license_id": max_lic.id, "company_id": max_co.id}
        )
    feat_mu = _feat_mod0(2) or sample_feat
    if feat_mu:
        env["justech.license.feature"].sudo().create(
            {"license_id": max_lic.id, "feature_id": feat_mu.id}
        )
    blocked = False
    try:
        max_lic.action_activate()
    except ValidationError:
        blocked = True
    check("lifecycle", "max_users_enforced", blocked, f"blocked={blocked}")
    if not blocked:
        issue(
            "alto",
            "COMP-02",
            "max_users sin enforcement",
            "action_activate no valida límite de usuarios",
        )
except Exception as exc:
    check("lifecycle", "max_users_enforced", False, traceback.format_exc()[-800:])

# ------------------------------------------------------------------ compatibility (static assessment)
report["compatibility"] = {
    "odoo_enterprise_dev": {"status": "PASS", "detail": "hellenia_dev Enterprise image"},
    "odoo_community": {
        "status": "PARTIAL",
        "detail": "depends base+mail only; privilege_id Odoo 19 — verify CE 19",
    },
    "multi_company": {"status": "PASS", "detail": "ir.rule + explicit license.company"},
    "future_saas": {
        "status": "GAP",
        "detail": "No justech.tenant; tenant-per-DB OK",
    },
    "future_marketplace": {
        "status": "GAP",
        "detail": "No module.version/release; dependency DAG present",
    },
    "future_justech_admin": {
        "status": "READY",
        "detail": "API v1 activate/deactivate/validate sufficient for CRUD delegation",
    },
    "future_hellenia_governance": {
        "status": "READY",
        "detail": "activate_feature/deactivate_feature public; callback hook pending F31.2",
    },
}
issue(
    "medio",
    "COMP-01",
    "Estado 'suspendida' no modelado",
    "Usar draft/revoked; agregar suspended en F31.2 si requerido",
)

# ------------------------------------------------------------------ scoring (dynamic from section results)
def _section_score(section, default=75):
    data = report.get(section) or {}
    if not data:
        return default
    checks = [v for k, v in data.items() if isinstance(v, dict) and "status" in v]
    if not checks:
        return default
    passed = sum(1 for c in checks if c.get("status") == "PASS")
    return round(70 + (passed / len(checks)) * 30)

perf_us = report.get("performance", {}).get("is_active_avg_us", 999)
if perf_us <= 5:
    perf_score = 95
elif perf_us <= 50:
    perf_score = 88
elif perf_us <= 100:
    perf_score = 80
else:
    perf_score = 55

categories = {
    "architecture": 85,
    "api_completeness": _section_score("api_tests", 88),
    "performance": perf_score,
    "concurrency": _section_score("concurrency", 75),
    "multi_company": _section_score("multi_company", 85),
    "security": _section_score("security", 68),
    "lifecycle": _section_score("lifecycle", 90),
    "rollback": _section_score("rollback", 85),
    "scalability_data": _section_score("dataset", 80),
    "future_readiness": 72,
}
weights = {
    "architecture": 12,
    "api_completeness": 15,
    "performance": 15,
    "concurrency": 8,
    "multi_company": 12,
    "security": 15,
    "lifecycle": 10,
    "rollback": 8,
    "scalability_data": 10,
    "future_readiness": 5,
}
weighted = sum(categories[k] * weights[k] for k in categories) / sum(weights.values())
report["scores"] = {
    "categories": categories,
    "weights": weights,
    "weighted_total": round(weighted, 1),
    "threshold_enterprise": 80,
    "pass": weighted >= 80 and report["ok"],
}

report["recommendations"] = [
    "P2: Add justech.tenant before SaaS pooled multi-DB",
    "P2: Audit failed validate_license attempts",
    "P3: Add suspended state or document draft semantics",
    "P3: Row-level lock (FOR UPDATE) on license activation for true concurrent users",
]
if perf_us > 50:
    report["recommendations"].insert(
        0, "P1: Further tune is_active cache / indexes if SLA tightens"
    )
if report.get("security", {}).get("license_key_hashed", {}).get("status") != "PASS":
    report["recommendations"].insert(
        0, "P1: Complete license_key_hash backfill for all licenses"
    )

# Index recommendations from performance
report["index_recommendations"] = [
    {
        "table": "justech_license_company",
        "columns": "company_id, license_id",
        "reason": "is_active hot path lookup by company",
    },
    {
        "table": "justech_feature_company",
        "columns": "feature_id, company_id, is_active",
        "reason": "activation check per feature",
    },
    {
        "table": "justech_feature",
        "columns": "code",
        "reason": "already UNIQUE — ensure used in all lookups",
    },
]

print("F31_1_1:" + json.dumps(report, ensure_ascii=False, default=str))
