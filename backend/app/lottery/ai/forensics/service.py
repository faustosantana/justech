"""Centralized forensic trace service for lottery chat turns."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.lottery.ai.forensics.compare import change_summary
from app.lottery.ai.forensics.context import get_correlation_id
from app.lottery.ai.forensics.redact import redact_obj


class ForensicTraceService:
    """Opt-in structured audit trail. No-op when disabled."""

    STAGE_FILES = {
        "request.incoming": "01_request_incoming.json",
        "conversation.state.before": "02_conversation_state_before.json",
        "intent.classification": "03_intent_classification.json",
        "prompt.compiled": "04_prompt_compiled.txt",
        "llm.request.prepared": "05_llm_payload_sanitized.json",
        "llm.response.raw": "06_huawei_raw_response_sanitized.json",
        "llm.response.extracted": "07_huawei_extracted_content.txt",
        "transformations": "08_transformations.json",
        "api_response.prepared": "09_backend_final_response.json",
        "frontend_response.received": "10_frontend_received_response.json",
        "frontend_message.rendered": "11_frontend_rendered_text.txt",
        "trace.summary": "12_trace_summary.md",
    }

    def __init__(self, correlation_id: str | None = None) -> None:
        self.correlation_id = correlation_id or get_correlation_id() or ""
        self.enabled = bool(getattr(settings, "lottery_forensic_trace_enabled", False))
        self.include_prompts = bool(
            getattr(settings, "lottery_forensic_trace_include_prompts", True)
        )
        self.include_raw = bool(
            getattr(settings, "lottery_forensic_trace_include_provider_raw", True)
        )
        self._events: list[dict[str, Any]] = []
        self._transforms: list[dict[str, Any]] = []
        self._t0 = time.perf_counter()
        self._dir: Path | None = None
        if self.enabled and self.correlation_id:
            root = Path(
                getattr(settings, "lottery_forensic_trace_dir", "")
                or ""
            )
            if not root or str(root) in {"", "."}:
                # backend/app/lottery/ai/forensics → repo root = parents[5]
                root = Path(__file__).resolve().parents[5] / "artifacts" / "forensics"
            else:
                root = Path(root)
            self._dir = root / self.correlation_id
            self._dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def enabled_globally(cls) -> bool:
        return bool(getattr(settings, "lottery_forensic_trace_enabled", False))

    def event(
        self,
        stage: str,
        *,
        component: str,
        file: str | None = None,
        function: str | None = None,
        input: Any = None,
        output: Any = None,
        error: str | None = None,
        extra: dict[str, Any] | None = None,
        duration_ms: float | None = None,
        track_transform: bool = False,
    ) -> None:
        if not self.enabled:
            return
        payload: dict[str, Any] = {
            "correlation_id": self.correlation_id,
            "stage": stage,
            "component": component,
            "file": file,
            "function": function,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "error": error,
        }
        if input is not None:
            payload["input"] = redact_obj(input)
        if output is not None:
            payload["output"] = redact_obj(output)
        if extra:
            payload["extra"] = redact_obj(extra)
        if track_transform:
            cmp = change_summary(input, output)
            payload.update(cmp)
            self._transforms.append(
                {
                    "stage": stage,
                    "component": component,
                    "file": file,
                    "function": function,
                    **cmp,
                    "input_preview": str(input)[:500] if input is not None else None,
                    "output_preview": str(output)[:500] if output is not None else None,
                }
            )
        self._events.append(payload)
        # Stage files are written explicitly via write_named() to avoid clobbering
        # rich payloads with thin event envelopes.

    def record_transform(
        self,
        stage: str,
        *,
        component: str,
        file: str,
        function: str,
        input: Any,
        output: Any,
        duration_ms: float | None = None,
    ) -> None:
        self.event(
            stage,
            component=component,
            file=file,
            function=function,
            input=input,
            output=output,
            duration_ms=duration_ms,
            track_transform=True,
        )

    def write_named(self, stage_key: str, content: Any, *, as_text: bool = False) -> None:
        if not self.enabled or not self._dir:
            return
        name = self.STAGE_FILES.get(stage_key, f"{stage_key}.json")
        path = self._dir / name
        if as_text:
            path.write_text(str(content or ""), encoding="utf-8")
            return
        path.write_text(
            json.dumps(redact_obj(content), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def finalize_summary(self, *, notes: list[str] | None = None) -> Path | None:
        if not self.enabled or not self._dir:
            return None
        self.write_named("transformations", {"events": self._transforms})
        # Find first transform that added Hallazgos headings or 50/90
        first_mutate = None
        for t in self._transforms:
            cs = t.get("change_summary") or {}
            if cs.get("added_headings") or cs.get("added_substr_50_90"):
                first_mutate = t
                break
        lines = [
            f"# Trace summary — `{self.correlation_id}`",
            "",
            f"- Events: {len(self._events)}",
            f"- Transforms: {len(self._transforms)}",
            f"- Elapsed ms: {round((time.perf_counter() - self._t0) * 1000, 2)}",
            "",
            "## First mutating transform",
            "",
        ]
        if first_mutate:
            lines.append(f"- Stage: `{first_mutate.get('stage')}`")
            lines.append(f"- Component: `{first_mutate.get('component')}`")
            lines.append(f"- File: `{first_mutate.get('file')}`")
            lines.append(f"- Function: `{first_mutate.get('function')}`")
            lines.append(
                f"- Added headings: {first_mutate.get('change_summary', {}).get('added_headings')}"
            )
            lines.append(
                f"- Added 50/90: {first_mutate.get('change_summary', {}).get('added_substr_50_90')}"
            )
        else:
            lines.append("- None detected among tracked transforms.")
        if notes:
            lines.extend(["", "## Notes", ""])
            lines.extend(f"- {n}" for n in notes)
        lines.append("")
        lines.append("## Event order")
        lines.append("")
        for e in self._events:
            lines.append(f"1. `{e.get('stage')}` — {e.get('component')}")
        path = self._dir / self.STAGE_FILES["trace.summary"]
        path.write_text("\n".join(lines), encoding="utf-8")
        # Full event log
        (self._dir / "00_events.json").write_text(
            json.dumps(self._events, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return self._dir

    def package_meta(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "correlation_id": self.correlation_id,
            "artifact_dir": str(self._dir) if self._dir else None,
            "event_count": len(self._events),
        }

    @staticmethod
    def hash_text(text: str) -> str:
        return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

    def _write_stage(self, stage: str, payload: dict[str, Any]) -> None:
        if not self._dir:
            return
        # Map known stages to numbered files; others append to events only
        if stage in self.STAGE_FILES and stage not in {
            "transformations",
            "trace.summary",
        }:
            name = self.STAGE_FILES[stage]
            path = self._dir / name
            # Prefer explicit write_named() payloads; do not clobber richer artifacts.
            if path.exists() and path.stat().st_size > 200:
                return
            if name.endswith(".txt") and "output" in payload:
                content = payload.get("output")
                if isinstance(content, dict) and "content" in content:
                    content = content["content"]
                path.write_text(str(content or ""), encoding="utf-8")
            elif name.endswith(".json"):
                path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8",
                )
