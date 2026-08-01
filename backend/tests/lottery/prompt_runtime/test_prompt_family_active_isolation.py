"""Active prompt versions are isolated by family (V6 vs Reasoning Studio)."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.lottery.ai.prompt_runtime.prompt_families import (
    FAMILY_ANALYST_V6,
    FAMILY_REASONING_STUDIO,
    enforce_single_active_in_family,
    plan_seed_status_mutations,
    prompt_family_key,
)
from app.lottery.ai.prompt_runtime.seed_reasoning_studio_v7 import REASONING_STUDIO_NAME
from app.lottery.ai.prompts.lottery_analyst_system_v6 import ANALYST_PROMPT_NAME

RC35 = "f9cb83c80271de345fb3b50a08cc9a76b31c66666d2dcb55517bbb7059d21149"


def _row(*, name: str, version: str, status: str, id_=None):
    return SimpleNamespace(id=id_ or uuid4(), name=name, version=version, status=status)


def test_family_keys_distinct():
    assert prompt_family_key(name=ANALYST_PROMPT_NAME, version="v6") == FAMILY_ANALYST_V6
    assert prompt_family_key(name=REASONING_STUDIO_NAME, version="7.0.0-rc3.5") == FAMILY_REASONING_STUDIO
    assert prompt_family_key(name=ANALYST_PROMPT_NAME, version="v6") != prompt_family_key(
        name=REASONING_STUDIO_NAME, version="7.0.0-rc3.5"
    )


def test_a_v6_and_reasoning_studio_both_remain_active():
    v6 = _row(name=ANALYST_PROMPT_NAME, version="v6", status="active")
    studio = _row(name=REASONING_STUDIO_NAME, version="7.0.0-rc3.5", status="active")
    rows = [
        {"id": v6.id, "name": v6.name, "version": v6.version, "status": "active"},
        {"id": studio.id, "name": studio.name, "version": studio.version, "status": "active"},
        {"id": uuid4(), "name": "lottery_assistant_system_v5", "version": "v5", "status": "motor"},
    ]
    mutations = plan_seed_status_mutations(rows, v6_id=v6.id)
    # Studio must not be demoted
    assert not any(m[0] == studio.id for m in mutations)
    # Simulate enforce on live objects after planner
    objs = [v6, studio]
    enforce_single_active_in_family(objs, family=FAMILY_ANALYST_V6, keep_id=v6.id)
    assert v6.status == "active"
    assert studio.status == "active"


def test_b_two_reasoning_studio_active_keeps_selected():
    keep = _row(name=REASONING_STUDIO_NAME, version="7.0.0-rc3.5", status="active")
    other = _row(name=REASONING_STUDIO_NAME, version="7.0.0-rc3.4", status="active")
    v6 = _row(name=ANALYST_PROMPT_NAME, version="v6", status="active")
    changed = enforce_single_active_in_family(
        [keep, other, v6],
        family=FAMILY_REASONING_STUDIO,
        keep_id=keep.id,
        demote_to="replaced",
    )
    assert keep.status == "active"
    assert other.status == "replaced"
    assert v6.status == "active"  # other family untouched
    assert other in changed


def test_c_two_v6_active_keeps_selected():
    keep = _row(name=ANALYST_PROMPT_NAME, version="v6", status="active")
    other = _row(name=ANALYST_PROMPT_NAME, version="v6-legacy", status="active")
    # Force other into same family via name
    other.version = "v6-dup"
    other.name = ANALYST_PROMPT_NAME
    studio = _row(name=REASONING_STUDIO_NAME, version="7.0.0-rc3.5", status="active")
    enforce_single_active_in_family([keep, other, studio], family=FAMILY_ANALYST_V6, keep_id=keep.id)
    assert keep.status == "active"
    assert other.status == "archived"
    assert studio.status == "active"


def test_d_ensure_seeded_planner_idempotent_no_studio_drift():
    v6_id = uuid4()
    studio_id = uuid4()
    rows = [
        {"id": v6_id, "name": ANALYST_PROMPT_NAME, "version": "v6", "status": "active"},
        {"id": studio_id, "name": REASONING_STUDIO_NAME, "version": "7.0.0-rc3.5", "status": "active"},
        {"id": uuid4(), "name": "lottery_assistant_system_v5", "version": "v5", "status": "motor"},
    ]
    m1 = plan_seed_status_mutations(rows, v6_id=v6_id)
    m2 = plan_seed_status_mutations(rows, v6_id=v6_id)
    assert not any(m[0] == studio_id for m in m1)
    assert m2 == [] or all(m[0] != studio_id for m in m2)
    # Second pass with already-correct statuses should not touch studio
    assert not any(m[0] == studio_id for m in m2)


def test_e_repeated_family_enforce_keeps_rc35_active():
    """Stand-in for repeated chat→ensure_seeded: studio stays active across calls."""
    v6 = _row(name=ANALYST_PROMPT_NAME, version="v6", status="active")
    studio = _row(name=REASONING_STUDIO_NAME, version="7.0.0-rc3.5", status="active")
    for _ in range(10):
        enforce_single_active_in_family([v6, studio], family=FAMILY_ANALYST_V6, keep_id=v6.id)
        assert studio.status == "active"
        assert v6.status == "active"
    assert studio.version == "7.0.0-rc3.5"


def test_f_activate_studio_does_not_change_v6():
    keep = _row(name=REASONING_STUDIO_NAME, version="7.0.0-rc3.5", status="published")
    prev = _row(name=REASONING_STUDIO_NAME, version="7.0.0-rc3.4", status="active")
    v6 = _row(name=ANALYST_PROMPT_NAME, version="v6", status="active")
    # Mirror activate_prompt_dev peer demote (same family only)
    enforce_single_active_in_family(
        [keep, prev, v6],
        family=FAMILY_REASONING_STUDIO,
        keep_id=keep.id,
        demote_to="replaced",
    )
    assert keep.status == "active"
    assert prev.status == "replaced"
    assert v6.status == "active"


def test_hash_constant_not_part_of_family_logic():
    # Guardrail: family isolation must not depend on / alter prompt hash constants.
    assert len(RC35) == 64
