"""Unit tests — Prompt Runtime Integration 1.0."""

from __future__ import annotations

import json

import pytest

from app.lottery.ai.analyst_reasoning.reasoning_prompt import (
    REASONING_PROMPT_VERSION,
    build_reasoning_messages,
    select_reasoning_prompt,
)
from app.lottery.ai.prompt_runtime.cache import cache_get, cache_invalidate, cache_set
from app.lottery.ai.prompt_runtime.compiler import PromptStudioCompiler
from app.lottery.ai.prompt_runtime.seed_reasoning_studio_v7 import (
    INITIAL_REASONING_STUDIO_BLOCKS,
    REASONING_STUDIO_SEMVER,
)
from app.lottery.ai.prompt_runtime.selector import PromptRuntimeSelector
from app.lottery.ai.prompt_runtime.validator import PromptStudioValidator


@pytest.fixture(autouse=True)
def _reset_prompt_cache_and_flags(monkeypatch):
    cache_invalidate()
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_runtime_mode",
        "legacy",
    )
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_studio_enabled",
        False,
    )
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_studio_version_id",
        "",
    )
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_ab_percent",
        0,
    )
    yield
    cache_invalidate()


def test_compile_deterministic_and_order():
    a = PromptStudioCompiler.compile(INITIAL_REASONING_STUDIO_BLOCKS)
    b = PromptStudioCompiler.compile(INITIAL_REASONING_STUDIO_BLOCKS)
    assert a["compiled_prompt_hash"] == b["compiled_prompt_hash"]
    assert a["assembly_order"][0] == "identidad"
    assert a["assembly_order"][-1] == "seguridad"
    assert "Hermes decide" in a["body"] or "herramientas" in a["body"].lower()


def test_required_blocks_and_secrets():
    bad = dict(INITIAL_REASONING_STUDIO_BLOCKS)
    bad["identidad"] = ""
    v = PromptStudioValidator.validate(bad)
    assert v["ok"] is False
    assert any(e["code"] == "empty_identidad" for e in v["errors"])

    secret = dict(INITIAL_REASONING_STUDIO_BLOCKS)
    secret["seguridad"] = "API_KEY=sk-abcdefghijklmnopqrstuvwxyz012345"
    v2 = PromptStudioValidator.validate(secret)
    assert v2["ok"] is False


def test_architecture_false_claims_rejected():
    bad = dict(INITIAL_REASONING_STUDIO_BLOCKS)
    bad["herramientas"] = "Tú ejecutas las herramientas y el modelo decide qué herramientas usar."
    v = PromptStudioValidator.validate(bad)
    assert v["ok"] is False
    assert any(e["code"] == "llm_runs_tools" for e in v["errors"])


def test_seed_v7_validates():
    v = PromptStudioValidator.validate(INITIAL_REASONING_STUDIO_BLOCKS)
    assert v["ok"] is True, v["errors"]
    assert v["chars"] > 500
    assert v["tokens_estimated"] > 100
    assert len(v["compiled_prompt_hash"]) == 64


def test_draft_does_not_enter_runtime(monkeypatch):
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_studio_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_runtime_mode",
        "studio",
    )
    compiled = PromptStudioCompiler.compile(INITIAL_REASONING_STUDIO_BLOCKS)

    def load_draft():
        return {
            "id": "draft-1",
            "version_id": "draft-1",
            "version": REASONING_STUDIO_SEMVER,
            "status": "draft",
            "body": compiled["body"],
            "checksum": compiled["compiled_prompt_hash"],
            "blocks": compiled["blocks"],
        }

    sel = PromptRuntimeSelector.select(
        mode_label="explain_evidence",
        mode_help="explica",
        reasoning_prompt_version=REASONING_PROMPT_VERSION,
        load_studio=load_draft,
    )
    assert sel.source == "legacy"
    assert sel.fallback_used is True


def test_active_studio_enters_runtime(monkeypatch):
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_studio_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_runtime_mode",
        "studio",
    )
    compiled = PromptStudioCompiler.compile(INITIAL_REASONING_STUDIO_BLOCKS)

    def load_active():
        return {
            "id": "active-1",
            "version_id": "active-1",
            "version": REASONING_STUDIO_SEMVER,
            "semantic_version": REASONING_STUDIO_SEMVER,
            "status": "active",
            "body": compiled["body"],
            "checksum": compiled["compiled_prompt_hash"],
            "blocks": compiled["blocks"],
        }

    sel = PromptRuntimeSelector.select(
        mode_label="explain_evidence",
        mode_help="explica",
        reasoning_prompt_version=REASONING_PROMPT_VERSION,
        load_studio=load_active,
    )
    assert sel.source == "studio"
    assert sel.fallback_used is False
    assert sel.prompt_version_id == "active-1"
    assert "CONTRATO_ARQUITECTURA" in sel.system_prompt
    assert compiled["compiled_prompt_hash"] == sel.compiled_prompt_hash


def test_published_not_active_does_not_enter(monkeypatch):
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_studio_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_runtime_mode",
        "studio",
    )
    compiled = PromptStudioCompiler.compile(INITIAL_REASONING_STUDIO_BLOCKS)

    def load_published():
        return {
            "version_id": "pub-1",
            "status": "approved",
            "body": compiled["body"],
            "checksum": compiled["compiled_prompt_hash"],
        }

    sel = PromptRuntimeSelector.select(
        mode_label="explain_evidence",
        mode_help="explica",
        reasoning_prompt_version=REASONING_PROMPT_VERSION,
        load_studio=load_published,
    )
    assert sel.source == "legacy"
    assert sel.fallback_used is True


def test_feature_flag_off_keeps_legacy(monkeypatch):
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_studio_enabled",
        False,
    )
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_runtime_mode",
        "studio",
    )
    compiled = PromptStudioCompiler.compile(INITIAL_REASONING_STUDIO_BLOCKS)

    def load_active():
        return {
            "version_id": "active-1",
            "status": "active",
            "body": compiled["body"],
            "checksum": compiled["compiled_prompt_hash"],
        }

    sel = PromptRuntimeSelector.select(
        mode_label="explain_evidence",
        mode_help="explica",
        reasoning_prompt_version=REASONING_PROMPT_VERSION,
        load_studio=load_active,
    )
    assert sel.source == "legacy"
    assert "Analyst Reasoning Layer" in sel.system_prompt


def test_cache_and_invalidation():
    cache_set(
        application="lottery_analyst_reasoning",
        version_id="v1",
        body="hello",
        compiled_prompt_hash=PromptStudioCompiler.hash_body("hello"),
        semantic_version="1",
        ttl_seconds=300,
    )
    hit = cache_get("lottery_analyst_reasoning")
    assert hit is not None
    assert hit.version_id == "v1"
    PromptRuntimeSelector.invalidate_cache()
    assert cache_get("lottery_analyst_reasoning") is None


def test_build_reasoning_messages_default_legacy():
    from app.lottery.ai.analyst_reasoning.evidence_package import EvidencePackage

    pkg = EvidencePackage(
        question="¿Qué significa?",
        subjects=["50", "90"],
        relation="same_day",
        counts={"total": 2},
        factual_answer="total 2",
    )
    msgs = build_reasoning_messages(package=pkg, mode="explain_evidence")
    assert msgs[0]["role"] == "system"
    assert "Analyst Reasoning Layer" in msgs[0]["content"]
    assert msgs[1]["role"] == "user"
    user = json.loads(msgs[1]["content"])
    assert "evidence_package" in user
    meta = msgs[0].get("_prompt_runtime") or {}
    assert meta.get("prompt_source") == "legacy"


def test_shadow_prepares_studio_keeps_legacy_user_facing(monkeypatch):
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_studio_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_runtime_mode",
        "shadow",
    )
    compiled = PromptStudioCompiler.compile(INITIAL_REASONING_STUDIO_BLOCKS)

    def load_active():
        return {
            "version_id": "active-1",
            "status": "active",
            "semantic_version": REASONING_STUDIO_SEMVER,
            "body": compiled["body"],
            "checksum": compiled["compiled_prompt_hash"],
        }

    sel = select_reasoning_prompt(mode="explain_evidence", load_studio=load_active)
    assert sel.source == "legacy"
    assert sel.shadow_system_prompt
    assert "PROMPT_SOURCE: prompt_studio" in sel.shadow_system_prompt


def test_ab_test_stable_bucket(monkeypatch):
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_studio_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_runtime_mode",
        "ab_test",
    )
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_ab_percent",
        100,
    )
    compiled = PromptStudioCompiler.compile(INITIAL_REASONING_STUDIO_BLOCKS)

    def load_active():
        return {
            "version_id": "active-1",
            "status": "active",
            "body": compiled["body"],
            "checksum": compiled["compiled_prompt_hash"],
            "semantic_version": "7.0.0-rc1",
        }

    sel = PromptRuntimeSelector.select(
        mode_label="explain_evidence",
        mode_help="x",
        reasoning_prompt_version="v",
        conversation_id="conv-1",
        load_studio=load_active,
    )
    assert sel.source == "studio"


def test_skip_mode_does_not_call_huawei_or_studio():
    from app.lottery.ai.analyst_reasoning.evidence_package import EvidencePackage
    from app.lottery.ai.analyst_reasoning.reasoning_layer import AnalystReasoningLayer

    pkg = EvidencePackage(question="x", factual_answer="local")
    called = {"n": 0}

    async def evil_caller(messages, max_tokens):
        called["n"] += 1
        return "bad", "m", {}

    import asyncio

    layer = AnalystReasoningLayer(huawei_caller=evil_caller)
    rr = asyncio.get_event_loop().run_until_complete(
        layer.run(package=pkg, mode="skip", factual_fallback="local")
    )
    assert called["n"] == 0
    assert rr.used_reasoning is False
    assert rr.text == "local"


def test_fallback_when_loader_raises(monkeypatch):
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_studio_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_runtime_mode",
        "studio",
    )

    def boom():
        raise RuntimeError("db down")

    sel = PromptRuntimeSelector.select(
        mode_label="explain_evidence",
        mode_help="x",
        reasoning_prompt_version="v",
        load_studio=boom,
    )
    assert sel.source == "legacy"
    assert sel.fallback_used is True


def test_corrupt_cache_falls_back_to_reload(monkeypatch):
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_studio_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_runtime_mode",
        "studio",
    )
    compiled = PromptStudioCompiler.compile(INITIAL_REASONING_STUDIO_BLOCKS)
    cache_set(
        application="lottery_analyst_reasoning",
        version_id="active-1",
        body="CORRUPT",
        compiled_prompt_hash="0" * 64,
        semantic_version="7.0.0-rc1",
        ttl_seconds=300,
    )

    def load_active():
        return {
            "version_id": "active-1",
            "status": "active",
            "semantic_version": REASONING_STUDIO_SEMVER,
            "body": compiled["body"],
            "checksum": compiled["compiled_prompt_hash"],
        }

    sel = PromptRuntimeSelector.select(
        mode_label="explain_evidence",
        mode_help="x",
        reasoning_prompt_version="v",
        load_studio=load_active,
    )
    assert sel.source == "studio"
    assert sel.compiled_prompt_hash == compiled["compiled_prompt_hash"]
