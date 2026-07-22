"""Margen inteligente — costo real + precio venta sugerido (listas indexadas)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class MarginConfig:
    freight_usd: Decimal = Decimal("25")
    tariff_pct: Decimal = Decimal("0")
    bank_fee_pct: Decimal = Decimal("2")
    itbis_pct: Decimal = Decimal("18")
    target_margin_pct: Decimal = Decimal("20")


@dataclass
class MarginBreakdown:
    cost_base: Decimal
    freight: Decimal
    tariff: Decimal
    bank_fee: Decimal
    total_cost: Decimal
    target_margin_pct: Decimal
    margin_amount: Decimal
    margin_pct_actual: Decimal
    itbis_amount: Decimal
    sale_price_suggested: Decimal
    currency: str
    quantity: int = 1
    total_cost_all: Decimal | None = None
    total_sale_all: Decimal | None = None
    total_margin_all: Decimal | None = None

    def as_dict(self) -> dict:
        def _v(x):
            if isinstance(x, Decimal):
                return float(x)
            return x

        return {k: _v(v) for k, v in {
            "cost_base": self.cost_base,
            "freight": self.freight,
            "tariff": self.tariff,
            "bank_fee": self.bank_fee,
            "total_cost": self.total_cost,
            "target_margin_pct": self.target_margin_pct,
            "margin_amount": self.margin_amount,
            "margin_pct_actual": self.margin_pct_actual,
            "itbis_amount": self.itbis_amount,
            "sale_price_suggested": self.sale_price_suggested,
            "currency": self.currency,
            "quantity": self.quantity,
            "total_cost_all": self.total_cost_all,
            "total_sale_all": self.total_sale_all,
            "total_margin_all": self.total_margin_all,
        }.items()}


class PriceMarginEngine:
    def calculate(
        self,
        cost: Decimal,
        *,
        currency: str = "USD",
        quantity: int = 1,
        config: MarginConfig | None = None,
    ) -> MarginBreakdown:
        cfg = config or MarginConfig()
        q = max(1, quantity)
        freight = cfg.freight_usd if currency.upper() == "USD" else (cfg.freight_usd * Decimal("58"))
        tariff = (cost * cfg.tariff_pct / Decimal("100")).quantize(Decimal("0.01"), ROUND_HALF_UP)
        subtotal = cost + freight + tariff
        bank_fee = (subtotal * cfg.bank_fee_pct / Decimal("100")).quantize(Decimal("0.01"), ROUND_HALF_UP)
        total_cost = (subtotal + bank_fee).quantize(Decimal("0.01"), ROUND_HALF_UP)

        margin_amount = (total_cost * cfg.target_margin_pct / Decimal("100")).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )
        sale_before_itbis = total_cost + margin_amount
        itbis = (sale_before_itbis * cfg.itbis_pct / Decimal("100")).quantize(Decimal("0.01"), ROUND_HALF_UP)
        sale = (sale_before_itbis + itbis).quantize(Decimal("0.01"), ROUND_HALF_UP)

        margin_pct = (
            ((sale - total_cost) / sale * Decimal("100")).quantize(Decimal("0.01"), ROUND_HALF_UP)
            if sale > 0
            else Decimal("0")
        )

        total_cost_all = (total_cost * q).quantize(Decimal("0.01"), ROUND_HALF_UP)
        total_sale_all = (sale * q).quantize(Decimal("0.01"), ROUND_HALF_UP)

        return MarginBreakdown(
            cost_base=cost,
            freight=freight,
            tariff=tariff,
            bank_fee=bank_fee,
            total_cost=total_cost,
            target_margin_pct=cfg.target_margin_pct,
            margin_amount=margin_amount,
            margin_pct_actual=margin_pct,
            itbis_amount=itbis,
            sale_price_suggested=sale,
            currency=currency,
            quantity=q,
            total_cost_all=total_cost_all,
            total_sale_all=total_sale_all,
            total_margin_all=(total_sale_all - total_cost_all).quantize(Decimal("0.01"), ROUND_HALF_UP),
        )
