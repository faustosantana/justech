"""Integration checks — payload shape for Prompt Runtime (legacy vs studio)."""

from __future__ import annotations

import json

import pytest

from app.lottery.ai.analyst_reasoning.evidence_package import EvidencePackage
from app.lottery.ai.analyst_reasoning.reasoning_prompt import (
    REASONING_PROMPT_VERSION,
    build_reasoning_messages,
)
from app.lottery.ai.prompt_runtime.compiler import PromptStudioCompiler
from app.lottery.ai.prompt_runtime.seed_reasoning_studio_v7 import INITIAL_REASONING_STUDIO_BLOCKS
from app.lottery.ai.prompt_runtime.seed_reasoning_studio_v7_rc2 import build_rc2_blocks
from app.lottery.ai.prompt_runtime.selector import PromptRuntimeSelector
from app.lottery.ai.prompt_runtime.validator import PromptStudioValidator


@pytest.fixture(autouse=True)
def _flags(monkeypatch):
    from app.lottery.ai.prompt_runtime.cache import cache_invalidate

    cache_invalidate()
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_runtime_mode",
        "legacy",
    )
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_studio_enabled",
        False,
    )
    yield
    cache_invalidate()


def _pkg() -> EvidencePackage:
    return EvidencePackage(
        question="¿Han coincidido el 50 y el 90?",
        subjects=["50", "90"],
        relation="same_day",
        counts={"total": 3},
        factual_answer="total 3",
    )


def test_legacy_system_is_analyst_reasoning_21():
    msgs = build_reasoning_messages(package=_pkg(), mode="explain_evidence")
    assert msgs[0]["role"] == "system"
    assert "Analyst Reasoning Layer de Lottery Analyst 2.1" in msgs[0]["content"]
    assert msgs[0]["_prompt_runtime"]["prompt_source"] == "legacy"
    user = json.loads(msgs[1]["content"])
    assert "evidence_package" in user
    assert user["evidence_package"]["subjects"] == ["50", "90"]


def test_studio_system_contains_compiled_exact_body(monkeypatch):
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
            "version_id": "active-rc",
            "status": "active",
            "semantic_version": "7.0.0-rc1",
            "body": compiled["body"],
            "checksum": compiled["compiled_prompt_hash"],
            "blocks": compiled["blocks"],
        }

    msgs = build_reasoning_messages(package=_pkg(), mode="explain_evidence", load_studio=load_active)
    system = msgs[0]["content"]
    assert system.startswith(compiled["body"]) or compiled["body"] in system
    assert msgs[0]["_prompt_runtime"]["prompt_source"] == "studio"
    assert msgs[0]["_prompt_runtime"]["compiled_prompt_hash"] == compiled["compiled_prompt_hash"]
    user = json.loads(msgs[1]["content"])
    assert user["evidence_package"]["counts"]["total"] == 3


def test_shadow_user_facing_legacy_payload(monkeypatch):
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
            "version_id": "active-rc",
            "status": "active",
            "semantic_version": "7.0.0-rc2",
            "body": compiled["body"],
            "checksum": compiled["compiled_prompt_hash"],
        }

    msgs = build_reasoning_messages(package=_pkg(), mode="explain_evidence", load_studio=load_active)
    assert "Analyst Reasoning Layer de Lottery Analyst 2.1" in msgs[0]["content"]
    meta = msgs[0]["_prompt_runtime"]
    assert meta["prompt_source"] == "legacy"
    assert meta.get("shadow_system_prompt")
    assert compiled["body"] in meta["shadow_system_prompt"]


def test_rc2_validates_and_has_ten_blocks():
    blocks = build_rc2_blocks()
    assert len(blocks) == 10
    v = PromptStudioValidator.validate(blocks)
    assert v["ok"] is True, v["errors"]
    assert v["chars"] > 40_000
    assert all((v["compiled"]["blocks"].get(k) or "").strip() for k in blocks)


def test_pinned_missing_falls_back(monkeypatch):
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_studio_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_runtime_mode",
        "studio",
    )
    monkeypatch.setattr(
        "app.lottery.ai.prompt_runtime.selector.settings.lottery_analyst_prompt_studio_version_id",
        "00000000-0000-0000-0000-000000000000",
    )
    sel = PromptRuntimeSelector.select(
        mode_label="explain_evidence",
        mode_help="x",
        reasoning_prompt_version=REASONING_PROMPT_VERSION,
        load_studio=lambda: None,
    )
    assert sel.source == "legacy"
    assert sel.fallback_used is True
