"""Lottery 3.0 hardening — gate backup + hot/cold intents + nav integrity mirror."""

from __future__ import annotations

import json
from pathlib import Path

from app.services.lottery_intent import LotterySessionContext, resolve_intent
from app.services.lottery_ai_contracts import LotteryToolName


ROOT = Path(__file__).resolve().parents[3]


def test_lottery_registry_legacy_hrefs_in_frontend():
    registry = ROOT / "frontend/src/lib/modules/registry.ts"
    text = registry.read_text(encoding="utf-8")
    # Locate lottery module block roughly
    assert 'id: "lottery"' in text
    required = [
        ('contentKey: "lottery:dashboard"', 'legacyHref: "/lottery"'),
        ('contentKey: "lottery:search"', 'legacyHref: "/lottery/search"'),
        ('contentKey: "lottery:lotteries"', 'legacyHref: "/lottery/lotteries"'),
        ('contentKey: "lottery:compare"', 'legacyHref: "/lottery/compare"'),
        ('contentKey: "lottery:statistics"', 'legacyHref: "/lottery/statistics"'),
        ('contentKey: "lottery:chat"', 'legacyHref: "/lottery/chat"'),
        ('contentKey: "lottery:saved"', 'legacyHref: "/lottery/saved"'),
        ('contentKey: "lottery:favorites"', 'legacyHref: "/lottery/favorites"'),
        ('contentKey: "lottery:admin-sync"', 'legacyHref: "/lottery/admin/sync"'),
        ('contentKey: "lottery:admin-scheduler"', 'legacyHref: "/lottery/admin/scheduler"'),
        ('contentKey: "lottery:admin-lotteries"', 'legacyHref: "/lottery/admin/lotteries"'),
    ]
    for key, href in required:
        assert key in text, key
        # href appears in same module; soft check
        assert href in text, href
    assert "group: \"Inicio\"" in text or "group: 'Inicio'" in text or 'group: "Inicio"' in text


def test_hot_cold_intents_not_generic():
    ctx = LotterySessionContext(last_lottery="Leidsa")
    cases = [
        ("Dame los 10 números más calientes de Leidsa en los últimos 30 sorteos.", "hot"),
        ("Dame los 10 más fríos por frecuencia.", "cold_frequency"),
        ("¿Cuáles llevan más tiempo sin aparecer?", "cold_interval"),
        ("¿Qué diferencia hay entre frío y atrasado?", "definition"),
        ("Compara los números calientes de Leidsa y Loteka.", "hot"),
        ("¿Qué significa un número caliente?", "definition"),
        ("Dame los números calientes de Leidsa.", "hot"),
    ]
    generic = "puedo consultar resultados históricos"
    for q, focus in cases:
        intent = resolve_intent(q, ctx)
        assert intent.kind == "tool", q
        assert intent.tool == LotteryToolName.GET_HOT_COLD, q
        assert intent.params.get("focus") == focus or (
            focus == "hot" and intent.params.get("focus") in {"hot", "both"}
        ), (q, intent.params)
        # clarify_message must not be the generic help
        assert generic not in (intent.clarify_message or "").lower()


def test_gate_backup_validate_and_status(tmp_path, monkeypatch):
    from app.config import settings
    from app.services import lottery_sync_gate_backup as gb

    monkeypatch.setattr(settings, "lottery_sync_gate_backup_dir", str(tmp_path))
    monkeypatch.setattr(settings, "lottery_sync_backup_max_age_hours", 24)
    monkeypatch.setattr(settings, "lottery_sync_gate_backup_auto_refresh", False)
    monkeypatch.setattr(settings, "lottery_sync_allowed_database", "jaios")

    dump = tmp_path / "pre_lottery_sync.dump"
    dump.write_bytes(b"X" * 2000)
    meta = {
        "checksum_sha256": __import__("hashlib").sha256(dump.read_bytes()).hexdigest(),
        "database_name": "jaios",
        "created_at": "2026-07-23T00:00:00+00:00",
        "size_bytes": 2000,
    }
    (tmp_path / "pre_lottery_sync.meta.json").write_text(json.dumps(meta), encoding="utf-8")

    info = gb.validate_gate_dump(dump, database_url="postgresql+asyncpg://jaios:x@postgres:5432/jaios")
    assert info["size_bytes"] >= 1000
    status = gb.gate_backup_status(database_url="postgresql+asyncpg://jaios:x@postgres:5432/jaios")
    assert status.ok is True
    assert status.path
    assert status.checksum_sha256_12


def test_gate_backup_missing_blocks(tmp_path, monkeypatch):
    from app.config import settings
    from app.services import lottery_sync_gate_backup as gb
    from app.services.lottery_sync_service import SyncEnvironmentGuardError
    import pytest

    monkeypatch.setattr(settings, "lottery_sync_gate_backup_dir", str(tmp_path))
    monkeypatch.setattr(settings, "lottery_sync_gate_backup_auto_refresh", False)
    with pytest.raises(SyncEnvironmentGuardError):
        gb.ensure_fresh_gate_backup(database_url="postgresql+asyncpg://jaios:x@postgres:5432/jaios")
