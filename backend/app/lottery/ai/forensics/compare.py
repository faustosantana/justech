"""Textual change summaries between forensic stages."""

from __future__ import annotations

import difflib
import re
from typing import Any

_HEADING_RE = re.compile(r"^\*\*(.+?)\*\*", re.M)


def change_summary(before: Any, after: Any) -> dict[str, Any]:
    a = "" if before is None else str(before)
    b = "" if after is None else str(after)
    changed = a != b
    heads_a = set(_HEADING_RE.findall(a))
    heads_b = set(_HEADING_RE.findall(b))
    ratio = difflib.SequenceMatcher(None, a[:8000], b[:8000]).ratio() if (a or b) else 1.0
    return {
        "changed": changed,
        "change_summary": {
            "input_length": len(a),
            "output_length": len(b),
            "added_headings": sorted(heads_b - heads_a),
            "removed_headings": sorted(heads_a - heads_b),
            "similarity_ratio": round(ratio, 4),
            "added_substr_50_90": ("50" in b and "90" in b) and not ("50" in a and "90" in a),
        },
    }
