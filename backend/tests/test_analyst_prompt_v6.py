"""LOTTERY_ANALYST_SYSTEM_V6 — prompt del Analista independiente del motor v5."""

from __future__ import annotations

from app.lottery.ai.prompts.lottery_analyst_system_v6 import (
    ANALYST_PROMPT_NAME,
    ANALYST_PROMPT_VERSION,
    ANALYST_V6,
    analyst_prompt_manifest,
    build_analyst_llm_messages,
    content_hash,
    get_analyst_prompt,
    get_analyst_system_prompt_text,
)
from app.lottery.ai.prompts.lottery_assistant_system_v1 import (
    get_active_prompt,
    get_motor_prompt,
    get_system_prompt_text,
)


def test_analyst_v6_identity_and_hash():
    p = get_analyst_prompt()
    assert p.name == ANALYST_PROMPT_NAME
    assert p.version == ANALYST_PROMPT_VERSION == "v6"
    assert p.status == "active"
    assert p.role == "analyst"
    assert "Analista IA" in p.body or "ANALISTA IA" in p.body
    assert "No eres el motor matemático" in p.body
    assert content_hash(p.body) == ANALYST_V6.content_hash
    assert analyst_prompt_manifest()["motor_prompt_untouched"] == "v5"


def test_motor_v5_untouched():
    motor = get_motor_prompt()
    assert motor.version == "v5"
    assert "v5" in motor.version.lower()
    # Maestro body must not be the analyst prompt
    assert "LOTTERY_ANALYST_SYSTEM_V6" not in (motor.body or "")
    assert get_analyst_system_prompt_text() != motor.body


def test_chat_active_is_analyst_v6():
    active = get_active_prompt()
    assert active.version == "v6"
    assert get_system_prompt_text() == get_analyst_system_prompt_text()
    assert "Nunca inventas datos históricos" in get_system_prompt_text()


def test_llm_message_order():
    msgs = build_analyst_llm_messages(
        question="¿Cuántas veces salió el 54?",
        template="El 54 aparece N veces.",
        facts={"number": 54, "total": 100},
        context={"active_numbers": [54]},
        intent="frequency",
        mode="tool",
        recent_messages=[{"role": "user", "content": "hola"}],
    )
    assert len(msgs) == 7
    assert msgs[0]["role"] == "system" and "GUARDRAILS" in msgs[0]["content"]
    assert msgs[1]["role"] == "system" and "ANALISTA IA" in msgs[1]["content"].upper()
    assert "Contexto estructurado" in msgs[2]["content"]
    assert "intención" in msgs[3]["content"].lower()
    assert "herramientas" in msgs[4]["content"].lower()
    assert "INSTRUCCIÓN DE RESPUESTA" in msgs[5]["content"]
    assert msgs[6]["role"] == "user"
    assert msgs[6]["content"] == "¿Cuántas veces salió el 54?"


def test_prompt_scenarios_coverage_markers():
    """Ensure V6 body covers required scenario policies (not full e2e)."""
    body = get_analyst_system_prompt_text().lower()
    for needle in (
        "hola",
        "histórico",
        "mismo día",
        "primera posición",
        "todas las posiciones",
        "compar",
        "después",
        "evidencia",
        "muestra",
        "no invent",
    ):
        assert needle in body, f"missing policy marker: {needle}"
