"""Forensic trace unit tests — no behavior change when disabled."""

from __future__ import annotations

from app.config import settings
from app.lottery.ai.forensics import (
    ForensicTraceService,
    get_correlation_id,
    new_correlation_id,
    set_correlation_id,
)
from app.lottery.ai.forensics.redact import redact_obj


def test_correlation_id_format_and_context():
    cid = new_correlation_id()
    assert cid.startswith("lottery-chat-")
    tok = set_correlation_id(cid)
    assert get_correlation_id() == cid
    from app.lottery.ai.forensics.context import reset_correlation_id

    reset_correlation_id(tok)


def test_redact_secrets():
    payload = {
        "Authorization": "Bearer super-secret-token-value",
        "api_key": "hk-abcdef",
        "messages": [{"role": "user", "content": "Hola"}],
        "nested": {"password": "x", "ok": 1},
    }
    out = redact_obj(payload)
    assert out["Authorization"] == "[REDACTED]"
    assert out["api_key"] == "[REDACTED]"
    assert out["nested"]["password"] == "[REDACTED]"
    assert out["messages"][0]["content"] == "Hola"
    assert out["nested"]["ok"] == 1


def test_disabled_is_noop(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "lottery_forensic_trace_enabled", False)
    monkeypatch.setattr(settings, "lottery_forensic_trace_dir", str(tmp_path))
    cid = new_correlation_id()
    set_correlation_id(cid)
    tr = ForensicTraceService(cid)
    tr.event("request.incoming", component="t", input={"a": 1})
    assert tr.finalize_summary() is None
    assert list(tmp_path.iterdir()) == [] or not (tmp_path / cid).exists()


def test_enabled_writes_artifacts(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "lottery_forensic_trace_enabled", True)
    monkeypatch.setattr(settings, "lottery_forensic_trace_dir", str(tmp_path))
    cid = new_correlation_id()
    set_correlation_id(cid)
    tr = ForensicTraceService(cid)
    tr.write_named("request.incoming", {"user_message": "Hola"})
    tr.record_transform(
        "response_formatter.output",
        component="format_analyst_response",
        file="response_formatter.py",
        function="format_analyst_response",
        input="texto plano",
        output="**Hallazgos**\n50\n**Detalle**\n**Interpretación**\n90",
    )
    path = tr.finalize_summary(notes=["unit"])
    assert path is not None
    assert (path / "08_transformations.json").exists()
    assert (path / "12_trace_summary.md").exists()
    summary = (path / "12_trace_summary.md").read_text(encoding="utf-8")
    assert "Hallazgos" in summary
    assert "response_formatter" in summary


def test_chat_send_response_accepts_forensic_field():
    from app.schemas.lottery_chat import ChatSendResponse

    r = ChatSendResponse(
        message={"id": "1", "role": "assistant", "content": "Hola"},
        user_message_id="u1",
        context={},
        forensic={"correlation_id": "lottery-chat-abc", "enabled": True},
    )
    assert r.forensic["correlation_id"].startswith("lottery-chat-")
