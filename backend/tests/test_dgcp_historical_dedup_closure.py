"""Tests — deduplicación, compare limits, job statuses, conservación de montos."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest

from app.services.dgcp_historical_identity import (
    can_auto_merge_institutions,
    can_auto_merge_suppliers,
    classify_name_pair,
    normalize_party_name,
    supplier_stable_key,
)
from app.services.dgcp_historical_job_status import (
    JOB_FAILED,
    JOB_SUCCESS,
    JOB_TIMEOUT,
    classify_exception,
    is_job_success,
    mark_job_complete,
    should_auto_retry,
)


def test_name_variants_same_identity_without_rpe():
    a = supplier_stable_key(rpe=None, name="ABC SRL", rnc=None)
    b = supplier_stable_key(rpe=None, name="ABC, S.R.L.", rnc=None)
    c = supplier_stable_key(rpe=None, name="ABC S.R.L.", rnc=None)
    assert a == b == c
    assert a.startswith("name-")


def test_same_rpe_one_identity_despite_name_variants():
    a = supplier_stable_key(rpe="56446", name="ABC SRL", rnc=None)
    b = supplier_stable_key(rpe="56446", name="ABC, S.R.L.", rnc=None)
    assert a == b == "rpe-56446"


def test_same_name_different_rpe_two_identities_no_auto_merge():
    a = supplier_stable_key(rpe="111", name="ABC SRL", rnc=None)
    b = supplier_stable_key(rpe="222", name="ABC, S.R.L.", rnc=None)
    assert a != b
    ok, criterion = can_auto_merge_suppliers(rnc_a=None, rnc_b=None, rpe_a="111", rpe_b="222")
    assert ok is False
    status, conf, reason = classify_name_pair(
        name_a="ABC SRL", name_b="ABC, S.R.L.", rpe_a="111", rpe_b="222"
    )
    assert status == "POSSIBLE_DUPLICATE"
    assert conf >= 0.85
    assert "NAME" in reason or "NORMALIZED" in reason


def test_auto_merge_only_on_exact_official_ids():
    assert can_auto_merge_suppliers(rnc_a="131123456", rnc_b="1-31-12345-6", rpe_a=None, rpe_b=None)[0]
    assert can_auto_merge_suppliers(rnc_a=None, rnc_b=None, rpe_a="56446", rpe_b="56446")[0]
    assert not can_auto_merge_suppliers(rnc_a=None, rnc_b=None, rpe_a="1", rpe_b="2")[0]


def test_institution_same_code_same_identity_name_only_candidate():
    ok, _ = can_auto_merge_institutions(code_a="237", code_b="237")
    assert ok
    ok2, _ = can_auto_merge_institutions(code_a="237", code_b="224")
    assert not ok2
    status, _, reason = classify_name_pair(
        name_a="Ministerio de Educación",
        name_b="Ministerio de Salud",
        rpe_a=None,
        rpe_b=None,
    )
    assert status in ("NOT_DUPLICATE", "REVIEW_REQUIRED")
    assert normalize_party_name("MINERD") != normalize_party_name("DGII")


def test_compare_request_max_three():
    from app.schemas.dgcp_historical_profiles import DGCPSupplierCompareRequest

    DGCPSupplierCompareRequest(keys=["a", "b", "c"])
    with pytest.raises(Exception):
        DGCPSupplierCompareRequest(keys=["a", "b", "c", "d"])


def test_job_success_not_overwritten_by_shell_timeout():
    job = SimpleNamespace(
        status="running",
        started_at=datetime.now(timezone.utc),
        completed_at=None,
        items_indexed=10,
        pages_indexed=1,
        contracts_indexed=2,
        error_message=None,
        source_status=None,
        rows_processed=None,
        duration_ms=None,
        result_hash=None,
        result_meta={},
    )
    mark_job_complete(job, status=JOB_SUCCESS, source_status="AVAILABLE")
    assert job.status == JOB_SUCCESS
    assert job.completed_at is not None
    mark_job_complete(job, status=JOB_TIMEOUT, error_message="shell timeout")
    assert job.status == JOB_SUCCESS
    assert job.result_meta.get("shell_post_timeout") is True
    assert is_job_success(job.status)
    assert should_auto_retry(job) is False


def test_job_real_timeout_and_source_unavailable():
    assert classify_exception(httpx.TimeoutException("t")) == JOB_TIMEOUT
    req = httpx.Request("GET", "https://example.com")
    resp = httpx.Response(502, request=req)
    assert classify_exception(httpx.HTTPStatusError("bad", request=req, response=resp)) == "SOURCE_UNAVAILABLE"
    job = SimpleNamespace(
        status="running",
        started_at=datetime.now(timezone.utc),
        completed_at=None,
        items_indexed=0,
        pages_indexed=0,
        contracts_indexed=0,
        error_message=None,
        source_status=None,
        rows_processed=None,
        duration_ms=None,
        result_hash=None,
        result_meta={},
    )
    mark_job_complete(job, status=JOB_FAILED, error_message="boom")
    assert job.status == JOB_FAILED
    assert should_auto_retry(job) is True
