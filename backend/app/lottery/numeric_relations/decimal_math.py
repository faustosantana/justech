"""Aritmética Decimal + ROUND_HALF_UP (equivalente Excel) para el motor."""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP


def validate_n(n: int) -> int:
    from app.lottery.numeric_relations.constants import N_MAX, N_MIN

    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError(f"n must be int, got {type(n).__name__}")
    if n < N_MIN or n > N_MAX:
        raise ValueError(f"n must be in [{N_MIN}, {N_MAX}], got {n}")
    return n


def sum_literal_digits(formatted_value: str) -> int:
    """Suma literal de dígitos; elimina solo el punto decimal."""
    digits = formatted_value.replace(".", "")
    if not digits.isdigit():
        raise ValueError(f"formatted_value has non-digit chars: {formatted_value!r}")
    return sum(int(ch) for ch in digits)


def digits_without_point(formatted_value: str) -> str:
    return formatted_value.replace(".", "")


def integer_digit_count(value: Decimal) -> int:
    """Cantidad de dígitos de la parte entera (truncada hacia abajo para positivos)."""
    if value < 0:
        raise ValueError("negative values are not supported")
    int_part = value.to_integral_value(rounding=ROUND_DOWN)
    return len(str(int(int_part)))


def quantize_half_up(value: Decimal, decimal_places: int) -> Decimal:
    if decimal_places < 0:
        raise ValueError("decimal_places must be >= 0")
    exp = Decimal(1).scaleb(-decimal_places)  # 10**(-decimal_places)
    return value.quantize(exp, rounding=ROUND_HALF_UP)


def format_fixed_decimals(value: Decimal, decimal_places: int) -> str:
    """Formatea con exactamente `decimal_places` decimales (ceros preservados)."""
    q = quantize_half_up(value, decimal_places)
    return f"{q:.{decimal_places}f}"
