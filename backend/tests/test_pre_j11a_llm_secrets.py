"""Pre-J11A — fundación de secretos LLM (TD-010). Solo secretos falsos."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.lottery import llm_secret_store as store
from app.services.credential_vault import decrypt_secret, encrypt_secret, mask_secret, redact_for_logs


@pytest.fixture(autouse=True)
def _clean():
    store.clear_store_for_tests()
    yield
    store.clear_store_for_tests()


def test_encrypt_decrypt_roundtrip():
    token = encrypt_secret("sk-test-fake-key-not-real")
    assert "sk-test" not in token
    assert decrypt_secret(token) == "sk-test-fake-key-not-real"


def test_mask_and_redact():
    assert mask_secret("abcdefghijklmnop") == "abcd…mnop"
    assert "[REDACTED]" in redact_for_logs("api_key=sk-secret-value-here")


def test_store_public_view_never_leaks_plaintext():
    view = store.store_secret(
        provider="openai",
        environment="test",
        plaintext="sk-fake-openai-key-000",
        actor_id=uuid4(),
    )
    dumped = str(view)
    assert "sk-fake-openai-key-000" not in dumped
    assert view["api_key_masked"]
    assert "api_key" not in view or view.get("api_key") is None


def test_rotate_and_runtime_reveal_env_separation():
    view = store.store_secret(
        provider="huawei_modelarts",
        environment="development",
        plaintext="huawei-fake-dev-key",
    )
    rid = __import__("uuid").UUID(view["id"])
    store.rotate_secret(rid, plaintext="huawei-fake-dev-key-rotated")
    plain = store.reveal_for_runtime(rid, environment="development")
    assert plain == "huawei-fake-dev-key-rotated"
    with pytest.raises(PermissionError):
        store.reveal_for_runtime(rid, environment="production")


def test_audit_has_no_secrets():
    store.store_secret(provider="compatible", environment="test", plaintext="compat-fake-key")
    for row in store.audit_trail():
        assert "compat-fake-key" not in str(row)
        assert "plaintext" not in row
