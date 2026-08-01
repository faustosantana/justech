"""Tests for run-scoped durable autonomous cert jobs."""

from __future__ import annotations

from pathlib import Path

import pytest

from run_paths import (
    assert_not_legacy_global,
    container_run_dir,
    host_run_dir,
    run_files,
    validate_run_id,
)


def test_run_directories_are_unique_per_run_id():
    a = container_run_dir("JOB_SMOKE_20260101T000000Z")
    b = container_run_dir("SHADOW25_20260101T000001Z")
    assert a != b
    assert a.name != b.name
    assert str(a).startswith("/tmp/prompt_cert/")


def test_host_and_container_share_run_id():
    rid = "JOB_SMOKE_20260101T010101Z"
    assert host_run_dir("/cert", rid).name == rid
    assert container_run_dir(rid).name == rid


def test_legacy_global_paths_forbidden():
    with pytest.raises(ValueError):
        assert_not_legacy_global("/tmp/shadow_eligible_out")
    with pytest.raises(ValueError):
        assert_not_legacy_global("/tmp/shadow_eligible_inner.log")
    assert_not_legacy_global("/tmp/prompt_cert/JOB_SMOKE_1/run.log")


def test_status_files_scoped_to_run(tmp_path: Path):
    rid = "JOB_SMOKE_UNIT"
    d = tmp_path / rid
    d.mkdir()
    files = run_files(d)
    assert files["heartbeat"].parent == d
    assert files["checkpoint"].parent == d
    assert files["exit_code"].parent == d
    other = run_files(tmp_path / "OTHER_RUN")
    assert other["heartbeat"] != files["heartbeat"]


def test_invalid_run_id_rejected():
    with pytest.raises(ValueError):
        validate_run_id("../etc")
    with pytest.raises(ValueError):
        validate_run_id("a/b")


def test_worker_pid_file_is_per_run(tmp_path: Path):
    r1 = run_files(tmp_path / "R1")
    r2 = run_files(tmp_path / "R2")
    r1["worker_pid"].parent.mkdir(parents=True)
    r2["worker_pid"].parent.mkdir(parents=True)
    r1["worker_pid"].write_text("111\n")
    r2["worker_pid"].write_text("222\n")
    assert r1["worker_pid"].read_text().strip() == "111"
    assert r2["worker_pid"].read_text().strip() == "222"


def test_stop_targets_only_run_pid_files(tmp_path: Path):
    """stop_autonomous_job.sh reads worker.pid/wrapper.pid under the run dir only."""
    files = run_files(tmp_path / "SHADOW25_X")
    files["worker_pid"].parent.mkdir(parents=True)
    files["worker_pid"].write_text("99999\n")
    files["wrapper_pid"].write_text("99998\n")
    assert files["worker_pid"].read_text().strip() == "99999"
    # No global pkill pattern in path helpers
    assert "shadow_eligible_out" not in str(files["worker_pid"])


def test_precheck_failed_marker_is_run_local(tmp_path: Path):
    files = run_files(tmp_path / "RUN_PRECHECK")
    files["precheck_failed"].parent.mkdir(parents=True)
    files["precheck_failed"].write_text("PROMPT_HASH_PRECHECK_FAILED\n")
    files["exit_code"].write_text("2\n")
    assert files["exit_code"].read_text().strip() == "2"
    assert files["precheck_failed"].exists()
