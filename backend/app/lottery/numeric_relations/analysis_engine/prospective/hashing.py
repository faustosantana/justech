"""Canonical hash and integrity for locked prospective predictions."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def build_lock_payload(
    *,
    inputs: dict[str, Any],
    target_date: str | None,
    lotteries: list[Any] | None,
    positions: list[Any] | None,
    candidates: list[dict[str, Any]],
    ranking: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    classifications: list[dict[str, Any]],
    tiebreak_rule: str,
    engine_version: str,
    table1_version: str,
    table2_version: str,
    locked_at: str,
    engine_commit: str | None = None,
) -> dict[str, Any]:
    return {
        "inputs": inputs,
        "target_date": target_date,
        "lotteries": lotteries or [],
        "positions": positions or [],
        "candidates": candidates,
        "ranking": ranking,
        "scores": scores,
        "classifications": classifications,
        "tiebreak_rule": tiebreak_rule,
        "engine_version": engine_version,
        "table1_version": table1_version,
        "table2_version": table2_version,
        "locked_at": locked_at,
        "engine_commit": engine_commit,
    }


def hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def verify_hash(payload: dict[str, Any], expected: str) -> bool:
    return hash_payload(payload) == expected
