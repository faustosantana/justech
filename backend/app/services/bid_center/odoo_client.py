"""Odoo Bid Center S2S client (disabled unless configured)."""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OdooBidCenterClient:
    def __init__(self) -> None:
        self.enabled = bool(getattr(settings, "bid_center_enabled", False))
        self.base_url = (getattr(settings, "bid_center_url", "") or "").rstrip("/")
        self.api_key = getattr(settings, "bid_center_api_key", "") or ""
        self.hmac_secret = getattr(settings, "bid_center_hmac_secret", "") or ""
        self.timeout = float(getattr(settings, "bid_center_timeout", 15) or 15)

    def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "status": "disabled"}
        if not self.base_url:
            return {"ok": False, "status": "missing_url"}
        try:
            data = self._request("GET", "/justech-bid-center/api/v1/health")
            return {"ok": True, "status": "up", "data": data}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "status": "error", "detail": str(exc)}

    def upsert_opportunity(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/justech-bid-center/api/v1/opportunities/upsert", payload)

    def show_interest(
        self,
        external_id: str,
        *,
        idempotency_key: str | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return self._request(
            "POST",
            f"/justech-bid-center/api/v1/opportunities/{external_id}/interest",
            body or {"origin": "jaios", "idempotency_key": idempotency_key},
            extra_headers=headers,
        )

    def push_analysis(self, external_id: str, analysis: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/justech-bid-center/api/v1/opportunities/{external_id}/analysis",
            {"analysis": analysis, "source": "jaios"},
        )

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("bid_center_disabled")
        if not self.base_url or not self.api_key:
            raise RuntimeError("bid_center_not_configured")
        url = self.base_url + path
        raw = "" if body is None else __import__("json").dumps(body, default=str)
        ts = str(int(time.time()))
        nonce = uuid.uuid4().hex
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Api-Key": self.api_key,
            "X-Timestamp": ts,
            "X-Nonce": nonce,
            "X-Correlation-Id": uuid.uuid4().hex,
        }
        if self.hmac_secret:
            msg = f"{ts}.{nonce}.{raw}".encode("utf-8")
            headers["X-Signature"] = hmac.new(
                self.hmac_secret.encode("utf-8"), msg, hashlib.sha256
            ).hexdigest()
        if extra_headers:
            headers.update(extra_headers)
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.request(method, url, content=raw.encode("utf-8") if raw else None, headers=headers)
            if resp.status_code >= 400:
                logger.warning("bid_center %s %s → %s %s", method, path, resp.status_code, resp.text[:300])
                resp.raise_for_status()
            return resp.json() if resp.content else {}


def get_bid_center_client() -> OdooBidCenterClient:
    return OdooBidCenterClient()
