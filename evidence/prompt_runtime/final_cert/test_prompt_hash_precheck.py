"""Harness prompt-hash precheck: resolve active hash, abort on mismatch, never product_fail."""

from __future__ import annotations

import pytest

from prompt_hash_precheck import (
    PromptHashPrecheckError,
    classify_hash_mismatch,
    resolve_expected_hash,
)

RC35 = "f9cb83c80271de345fb3b50a08cc9a76b31c66666d2dcb55517bbb7059d21149"
RC34 = "41c64a0fc7c303222c2b492e82a0ea51cec6c16139bc2f0cde9ec9e9da642ff9"
VID35 = "10a3440c-60ff-4882-b5b1-1ba240df809e"


def _status(hash_: str = RC35, version: str = "7.0.0-rc3.5", vid: str = VID35) -> dict:
    return {
        "active": {
            "id": vid,
            "version": version,
            "checksum": hash_,
        }
    }


def _freeze(hash_: str = RC35, version: str = "7.0.0-rc3.5", vid: str = VID35) -> dict:
    return {
        "version_id": vid,
        "semantic_version": version,
        "compiled_prompt_hash": hash_,
        "expected_hash": hash_,
    }


def test_rc35_active_expected_rc35_pass():
    resolved = resolve_expected_hash(
        status=_status(),
        env_expected_hash=RC35,
        freeze=_freeze(),
    )
    assert resolved.expected_hash == RC35
    assert resolved.active_hash == RC35
    assert resolved.hash_source == "env"


def test_rc35_active_expected_rc34_precheck_abort():
    with pytest.raises(PromptHashPrecheckError) as ei:
        resolve_expected_hash(
            status=_status(),
            env_expected_hash=RC34,
            freeze=_freeze(),
        )
    assert "PROMPT_HASH_PRECHECK_FAILED" in str(ei.value)


def test_empty_expected_resolves_from_status_api():
    resolved = resolve_expected_hash(
        status=_status(),
        env_expected_hash=None,
        freeze=None,
    )
    assert resolved.expected_hash == RC35
    assert resolved.hash_source == "runtime_status"


def test_status_api_inaccessible_aborts_no_legacy_hash():
    def _boom():
        raise PromptHashPrecheckError("PROMPT_HASH_PRECHECK_FAILED: status API inaccessible (Timeout)")

    with pytest.raises(PromptHashPrecheckError) as ei:
        resolve_expected_hash(
            status=None,
            env_expected_hash=None,
            freeze=_freeze(),
            status_fetcher=_boom,
        )
    msg = str(ei.value)
    assert "PROMPT_HASH_PRECHECK_FAILED" in msg
    assert "inaccessible" in msg
    assert RC34 not in msg


def test_prompt_change_after_freeze_aborts():
    with pytest.raises(PromptHashPrecheckError) as ei:
        resolve_expected_hash(
            status=_status(hash_=RC35),
            env_expected_hash=None,
            freeze=_freeze(hash_=RC34, version="7.0.0-rc3.4", vid="c41ec4c5-1bd5-430f-85c5-e9546e176709"),
        )
    assert "PROMPT_HASH_PRECHECK_FAILED" in str(ei.value)


def test_hash_mismatch_never_product_fail():
    cls = classify_hash_mismatch(RC34, RC35)
    assert cls == "harness_configuration_error"
    assert cls != "product_fail"


def test_hash_mismatch_classified_harness_configuration_error():
    assert classify_hash_mismatch(RC34, RC35) == "harness_configuration_error"
    assert classify_hash_mismatch(RC35, RC35) is None
    assert classify_hash_mismatch(None, RC35) == "harness_configuration_error"
