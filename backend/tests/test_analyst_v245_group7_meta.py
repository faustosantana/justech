"""v2.4.5 Grupo 7 — H.5–H.9 meta continuity without reopening prior subject.

Root cause: after H.4 corrected to 97, focus_stack still held [22, 97] and LLM
synthesis apologized about 22 vs 97. ConversationPolicy pins the active subject
and forces local template for meta turns (no LLM rewrite).
"""

from __future__ import annotations

from app.lottery.ai.analyst.conversation_brain import ConversationBrain
from app.lottery.ai.conversation_state import ConversationState, UnderstandingResult
from app.lottery.ai.turn_policy import ConversationPolicy


def test_h4_correction_replaces_focus_stack():
    st = ConversationState(active_numbers=["22"], focus_stack=["22"])
    und = UnderstandingResult(intent="last_times", numbers=["97"])
    st2 = ConversationBrain(st).apply_resolution(
        understanding=und,
        resolution={
            "numbers": ["97"],
            "raw_message": "No, me refiero al 97.",
            "resolved_refs": ["correction_or_meta", "message_numbers"],
        },
    )
    assert st2.active_numbers == ["97"]
    assert st2.focus_stack == ["97"]
    assert st2.force_local_template is False


def test_h5_meta_pins_active_and_forces_template():
    st = ConversationState(
        active_numbers=["97"],
        focus_stack=["22", "97"],
        last_intent="last_occurrence",
    )
    und = UnderstandingResult(intent="last_times", numbers=["97"])
    st2 = ConversationBrain(st).apply_resolution(
        understanding=und,
        resolution={
            "numbers": ["97"],
            "inherit_active_number": True,
            "raw_message": "Eso no fue lo que pregunté.",
            "resolved_refs": ["correction_or_meta"],
        },
    )
    assert st2.focus_stack == ["97"]
    assert st2.active_numbers == ["97"]
    assert st2.force_local_template is True
    assert ConversationPolicy.should_force_local_template(st2, "Eso no fue lo que pregunté.")


def test_policy_meta_continuity_detection():
    assert ConversationPolicy.is_meta_continuity("Eso no fue lo que pregunté.")
    assert ConversationPolicy.is_meta_continuity("Revísalo otra vez.")
    assert ConversationPolicy.is_meta_continuity("¿Estás seguro?")
    assert ConversationPolicy.is_subject_correction("No, me refiero al 97.")
    assert not ConversationPolicy.is_meta_continuity("No, me refiero al 97.")
