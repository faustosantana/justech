"""Ingram Micro — catálogo live vía API Xvantage (+ fallback sesión portal)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.integrations.suppliers.base import SupplierConnector, SupplierProduct
from integrations.suppliers.config import IngramConnectorConfig
from integrations.suppliers.rate_limit import SupplierRateLimiter

_TOKEN_CACHE: dict[str, tuple[str, float]] = {}
_LIMITER = SupplierRateLimiter()


class IngramConnector(SupplierConnector):
    provider_id = "ingram"
    integration_type = "scraper"

    def __init__(
        self,
        config: IngramConnectorConfig,
        *,
        tenant_id: str | None = None,
        portal_cookies: list[dict[str, str]] | None = None,
        session_token: str = "",
    ):
        self.config = config
        self.tenant_id = tenant_id or "global"
        self._rate_key = f"{self.tenant_id}:ingram"
        self._last_error: str | None = None
        self._portal_cookies = portal_cookies or []
        self._session_token = session_token

    async def search_products(self, query: str, *, limit: int = 20) -> list[SupplierProduct]:
        if not self.config.enabled:
            return []
        if not query.strip():
            return []

        if self.config.demo_mode and not self.config.configured:
            return self._demo_products(query, limit=limit)

        await _LIMITER.acquire(self._rate_key)

        if self.config.client_id and self.config.client_secret:
            try:
                items = await self._search_api(query, limit=limit)
                if items:
                    return items
            except Exception as exc:
                self._last_error = f"api: {exc}"

        if self._portal_cookies or self._session_token:
            try:
                items = await self._search_cep_session(query, limit=limit)
                if items:
                    return items
            except Exception as exc:
                self._last_error = f"cep: {exc}"

        if self.config.username and self.config.password and not self.config.is_cep_portal:
            try:
                items = await self._search_portal_session(query, limit=limit)
                if items:
                    return items
            except Exception as exc:
                self._last_error = f"portal: {exc}"

        return []

    async def get_price(self, sku: str) -> SupplierProduct | None:
        rows = await self.search_products(sku, limit=5)
        sku_l = sku.lower()
        for row in rows:
            if (row.sku or "").lower() == sku_l:
                return row
        return rows[0] if rows else None

    async def get_stock(self, sku: str) -> int | None:
        row = await self.get_price(sku)
        return row.stock if row else None

    async def sync_catalog(self) -> dict:
        return {
            "ok": False,
            "message": "Ingram no soporta sync_catalog completo — use search_products.",
            "provider": self.provider_id,
        }

    async def health_check(self) -> dict[str, Any]:
        if not self.config.enabled:
            return {"ok": False, "status": "disabled", "message": "Ingram deshabilitado"}
        if self.config.demo_mode and not self.config.configured:
            return {"ok": True, "status": "demo", "message": "Modo demo activo"}
        if not self.config.configured and not self._portal_cookies and not self._session_token:
            return {"ok": False, "status": "not_configured", "message": "Configure API keys o usuario portal"}
        if self.config.is_cep_portal and not self.config.client_id and not self._portal_cookies and not self._session_token:
            return {
                "ok": False,
                "status": "awaiting_mfa",
                "message": "Ingrese el código de Authenticator arriba para conectar Ingram CEP",
                "portal_url": self.config.portal_url,
                "auth_provider": "okta",
            }
        try:
            rows = await self.search_products("dell", limit=1)
            detail = self._last_error
            if not rows and detail:
                return {
                    "ok": False,
                    "status": "error",
                    "message": detail,
                    "portal_url": self.config.portal_url,
                }
            return {
                "ok": bool(rows),
                "status": "connected" if rows else "empty",
                "message": f"{len(rows)} resultado(s) de prueba",
                "source": "api" if self.config.client_id else ("cep_session" if self._portal_cookies else "portal_session"),
                "portal_url": self.config.portal_url,
                "detail": detail,
            }
        except Exception as exc:
            return {"ok": False, "status": "error", "message": str(exc), "detail": self._last_error}

    async def _search_api(self, query: str, *, limit: int) -> list[SupplierProduct]:
        token = await self._oauth_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "IM-CustomerNumber": self.config.customer_number,
            "IM-CountryCode": self.config.country_code,
            "IM-CorrelationID": str(uuid.uuid4()),
            "IM-SenderID": self.config.sender_id,
        }
        url = f"{self.config.api_root}/resellers/v6/catalog"
        params = {
            "keyword": query.strip(),
            "pageSize": min(limit, 50),
            "pageNumber": 1,
        }
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.get(url, headers=headers, params=params)
            r.raise_for_status()
            data = r.json()

        catalog = data.get("catalog") or data.get("products") or data.get("items") or []
        if isinstance(data, list):
            catalog = data

        return [self._map_api_row(row) for row in catalog[:limit] if row]

    async def _oauth_token(self) -> str:
        cache_key = f"{self.config.client_id}:{self.config.use_sandbox}"
        import time

        cached = _TOKEN_CACHE.get(cache_key)
        if cached and time.time() < cached[1]:
            return cached[0]

        token_url = f"{self.config.api_base_url.rstrip('/')}/oauth/oauth20/token"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            r.raise_for_status()
            payload = r.json()

        token = payload["access_token"]
        expires = time.time() + int(payload.get("expires_in", 3600)) - 120
        _TOKEN_CACHE[cache_key] = (token, expires)
        return token

    async def _search_portal_session(self, query: str, *, limit: int) -> list[SupplierProduct]:
        """Fallback: sesión portal Xvantage CEP (mi.ingrammicro.com). Requiere MFA — suele fallar."""
        login_url = self.config.login_url
        base = self.config.portal_url.rstrip("/")
        search_url = f"{base}/search?q={quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; JAIOS/1.0; +https://justech.do)",
            "Accept": "text/html,application/json,*/*",
            "Origin": "https://mi.ingrammicro.com",
            "Referer": login_url,
        }

        async with httpx.AsyncClient(timeout=60, follow_redirects=True, headers=headers) as client:
            await client.get(login_url)
            login_resp = await client.post(
                "https://myaccount.ingrammicro.com/api/v1/authn",
                json={"username": self.config.username, "password": self.config.password},
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
            if login_resp.status_code >= 400:
                self._last_error = f"authn {login_resp.status_code}: {login_resp.text[:200]}"
                login_resp.raise_for_status()

            payload = login_resp.json()
            status = payload.get("status") or payload.get("state")
            if status and str(status).upper() in ("MFA_REQUIRED", "MFA_CHALLENGE"):
                self._last_error = "Ingram requiere MFA (Google/Microsoft Authenticator)"
                return []

            search_resp = await client.get(search_url)
            if search_resp.status_code >= 400:
                self._last_error = f"search {search_resp.status_code}"
                search_resp.raise_for_status()
            body = search_resp.text

        embedded = self._extract_embedded_json(body)
        if embedded:
            return self._parse_embedded_catalog(embedded, limit=limit)

        return self._parse_html_cards(body, limit=limit)

    async def _search_cep_session(self, query: str, *, limit: int) -> list[SupplierProduct]:
        """Búsqueda catálogo CEP con cookies de sesión post-MFA."""
        from integrations.suppliers.ingram_okta import cookies_to_header

        cookie_header = cookies_to_header(self._portal_cookies)
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; JAIOS/1.0; +https://justech.do)",
            "Accept": "application/json, text/plain, */*",
            "Cookie": cookie_header,
            "Origin": "https://mi.ingrammicro.com",
            "Referer": f"{self.config.portal_url.rstrip('/')}/",
        }
        params_list = [
            ("https://mi.ingrammicro.com/api/product/v1/search", {"keyword": query.strip(), "pageSize": limit}),
            (
                "https://mi.ingrammicro.com/api/product-discovery/v1/products/search",
                {"searchCriteria": query.strip(), "pageSize": limit},
            ),
            (
                "https://mi.ingrammicro.com/api/catalog/v1/products",
                {"keyword": query.strip(), "pageSize": limit},
            ),
        ]

        async with httpx.AsyncClient(timeout=45, follow_redirects=True, headers=headers) as client:
            for url, params in params_list:
                try:
                    resp = await client.get(url, params=params)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    rows = self._extract_catalog_rows(data)
                    if rows:
                        products = [self._map_api_row(row) for row in rows[:limit]]
                        for product in products:
                            product.source = "ingram_cep_session"
                            if product.raw is not None:
                                product.raw["verification_required"] = True
                        return products
                except Exception as exc:
                    self._last_error = str(exc)
                    continue

        search_url = f"{self.config.portal_url.rstrip('/')}/search?q={quote_plus(query)}"
        try:
            async with httpx.AsyncClient(timeout=45, follow_redirects=True, headers=headers) as client:
                resp = await client.get(search_url)
                resp.raise_for_status()
                embedded = self._extract_embedded_json(resp.text)
                if embedded:
                    return self._parse_embedded_catalog(embedded, limit=limit)
                return self._parse_html_cards(resp.text, limit=limit)
        except Exception as exc:
            self._last_error = (
                f"CEP sin respuesta desde el servidor ({exc}). "
                "MFA conectado, pero mi.ingrammicro.com no responde desde este VPS."
            )
            return []

    @staticmethod
    def _extract_catalog_rows(data: Any) -> list[dict]:
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
        for key in ("catalog", "products", "items", "records", "data", "productSummaries"):
            block = data.get(key) if isinstance(data, dict) else None
            if isinstance(block, list) and block:
                return [r for r in block if isinstance(r, dict)]
        return []

    @staticmethod
    def _extract_embedded_json(html: str) -> Any | None:
        for pattern in (
            r'__NEXT_DATA__"\s*type="application/json"\s*>\s*({.*?})\s*</script>',
            r"window\.__INITIAL_STATE__\s*=\s*({.*?});",
        ):
            m = re.search(pattern, html, re.S)
            if m:
                try:
                    import json

                    return json.loads(m.group(1))
                except Exception:
                    continue
        return None

    def _parse_embedded_catalog(self, data: Any, *, limit: int) -> list[SupplierProduct]:
        found: list[dict] = []

        def walk(node: Any) -> None:
            if len(found) >= limit:
                return
            if isinstance(node, dict):
                if any(k in node for k in ("ingramPartNumber", "vendorPartNumber", "sku")):
                    found.append(node)
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(data)
        return [self._map_api_row(row) for row in found[:limit]]

    def _parse_html_cards(self, html: str, *, limit: int) -> list[SupplierProduct]:
        items: list[SupplierProduct] = []
        for block in re.findall(r'class="[^"]*product[^"]*"[^>]*>(.*?)</div>', html, re.I | re.S)[: limit * 3]:
            sku_m = re.search(r"(?:SKU|Part\s*#|VPN)[:\s]*([A-Z0-9\-]+)", block, re.I)
            price_m = re.search(r"\$\s*([\d,]+\.?\d*)", block)
            name_m = re.search(r"<h[1-6][^>]*>([^<]+)", block, re.I)
            if not sku_m and not name_m:
                continue
            price = None
            if price_m:
                try:
                    price = Decimal(price_m.group(1).replace(",", ""))
                except InvalidOperation:
                    price = None
            items.append(
                SupplierProduct(
                    sku=sku_m.group(1) if sku_m else (name_m.group(1).strip()[:32] if name_m else "unknown"),
                    name=name_m.group(1).strip() if name_m else "Producto Ingram",
                    price=price,
                    currency="USD",
                    stock=None,
                    source="ingram_portal_scraper",
                    updated_at=datetime.now(UTC),
                    raw={"verification_required": True, "parse": "html"},
                )
            )
            if len(items) >= limit:
                break
        return items

    def _map_api_row(self, row: dict) -> SupplierProduct:
        sku = (
            row.get("ingramPartNumber")
            or row.get("vendorPartNumber")
            or row.get("sku")
            or row.get("partNumber")
            or ""
        )
        name = row.get("description") or row.get("title") or row.get("productTitle") or sku
        pricing = row.get("pricing") or row.get("price") or {}
        if isinstance(pricing, list) and pricing:
            pricing = pricing[0]
        price_val = (
            pricing.get("customerPrice")
            or pricing.get("retailPrice")
            or pricing.get("price")
            or row.get("customerPrice")
        )
        currency = pricing.get("currencyCode") or row.get("currencyCode") or "USD"
        avail = row.get("availability") or {}
        if isinstance(avail, list) and avail:
            avail = avail[0]
        stock = avail.get("totalAvailability") or avail.get("quantity") or row.get("stock")

        price = None
        if price_val is not None:
            try:
                price = Decimal(str(price_val))
            except InvalidOperation:
                price = None

        stock_i = None
        if stock is not None:
            try:
                stock_i = int(stock)
            except (TypeError, ValueError):
                stock_i = None

        return SupplierProduct(
            sku=str(sku),
            name=str(name)[:512],
            price=price,
            currency=str(currency).upper()[:8],
            stock=stock_i,
            source="ingram_xvantage_api",
            updated_at=datetime.now(UTC),
            raw={
                "vendor": row.get("vendorName") or row.get("vendor"),
                "mpn": row.get("vendorPartNumber"),
                "verification_required": False,
            },
        )

    @staticmethod
    def _demo_products(query: str, *, limit: int) -> list[SupplierProduct]:
        q = query.lower()
        catalog = [
            SupplierProduct(
                sku="IM-DELL-PRO14-001",
                name="Dell Pro 14 PC14250 16GB 512GB W11P",
                price=Decimal("818.51"),
                currency="USD",
                stock=25,
                source="ingram_demo",
                updated_at=datetime.now(UTC),
                raw={"vendor": "Dell", "demo": True},
            ),
            SupplierProduct(
                sku="IM-DELL-PRO14-002",
                name="Dell Pro 14 PC14250 16GB 512GB — canal alterno",
                price=Decimal("832.00"),
                currency="USD",
                stock=14,
                source="ingram_demo",
                updated_at=datetime.now(UTC),
                raw={"vendor": "Dell", "demo": True},
            ),
        ]
        if "dell" in q or "laptop" in q or "latitude" in q or "pro 14" in q:
            return catalog[:limit]
        return catalog[: min(1, limit)]
