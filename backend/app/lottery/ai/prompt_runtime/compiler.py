"""Canonical Prompt Studio compiler — single backend source of truth."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.lottery.ai.prompt_studio import (
    PROMPT_STUDIO_BLOCKS,
    compile_prompt_from_blocks,
    estimate_tokens,
)

# Canonical order (must match PROMPT_STUDIO_BLOCKS keys)
CANONICAL_BLOCK_ORDER: list[str] = [b["key"] for b in PROMPT_STUDIO_BLOCKS]

_MAX_COMPILED_CHARS = 120_000


def _normalize_newlines(text: str) -> str:
    t = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    # Trim trailing spaces per line; keep intentional blank lines (collapse 3+ → 2)
    lines = [ln.rstrip() for ln in t.split("\n")]
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


class PromptStudioCompiler:
    """Compile editorial blocks → immutable body + SHA-256."""

    application = "lottery_analyst_reasoning"

    @classmethod
    def compile(cls, blocks: dict[str, str] | None) -> dict[str, Any]:
        normalized: dict[str, str] = {}
        for key in CANONICAL_BLOCK_ORDER:
            raw = (blocks or {}).get(key) or ""
            normalized[key] = _normalize_newlines(raw)

        compiled = compile_prompt_from_blocks(normalized, assembly_order=CANONICAL_BLOCK_ORDER)
        body = _normalize_newlines(str(compiled.get("body") or ""))
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        return {
            "application": cls.application,
            "body": body,
            "blocks": normalized,
            "fragments": compiled.get("fragments") or [],
            "assembly_order": list(CANONICAL_BLOCK_ORDER),
            "chars": len(body),
            "tokens_estimated": estimate_tokens(body),
            "compiled_prompt_hash": digest,
            "max_chars": _MAX_COMPILED_CHARS,
            "within_limit": len(body) <= _MAX_COMPILED_CHARS,
        }

    @classmethod
    def hash_body(cls, body: str) -> str:
        return hashlib.sha256(_normalize_newlines(body).encode("utf-8")).hexdigest()
