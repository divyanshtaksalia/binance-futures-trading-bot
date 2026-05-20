from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")
VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}


class ValidationError(ValueError):
    """Raised when CLI order input is invalid."""


@dataclass(frozen=True, slots=True)
class OrderInput:
    symbol: str
    side: str
    order_type: str
    quantity: str
    price: str | None = None
    stop_price: str | None = None
    time_in_force: str = "GTC"


def validate_order_input(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: str | None,
    stop_price: str | None,
    time_in_force: str,
) -> OrderInput:
    normalized_symbol = symbol.strip().upper()
    normalized_side = side.strip().upper()
    normalized_type = order_type.strip().upper()
    normalized_time_in_force = time_in_force.strip().upper()

    if not SYMBOL_PATTERN.fullmatch(normalized_symbol):
        raise ValidationError("symbol must look like a Binance pair, for example BTCUSDT.")
    if normalized_side not in VALID_SIDES:
        raise ValidationError("side must be BUY or SELL.")
    if normalized_type not in VALID_ORDER_TYPES:
        raise ValidationError(f"order type must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}")

    quantity_value = _positive_decimal(quantity, "quantity")
    normalized_quantity = _decimal_to_string(quantity_value)

    normalized_price: str | None = None
    if normalized_type == "LIMIT":
        if price is None:
            raise ValidationError("price is required for LIMIT orders.")
        price_value = _positive_decimal(price, "price")
        normalized_price = _decimal_to_string(price_value)
    elif price is not None:
        raise ValidationError("price is only valid for LIMIT orders.")

    normalized_stop_price: str | None = None
    if normalized_type == "STOP_MARKET":
        if stop_price is None:
            raise ValidationError("stop_price is required for STOP_MARKET orders.")
        stop_val = _positive_decimal(stop_price, "stop_price")
        normalized_stop_price = _decimal_to_string(stop_val)
    elif stop_price is not None:
        raise ValidationError("stop_price is only valid for STOP_MARKET orders.")

    return OrderInput(
        symbol=normalized_symbol,
        side=normalized_side,
        order_type=normalized_type,
        quantity=normalized_quantity,
        price=normalized_price,
        stop_price=normalized_stop_price,
        time_in_force=normalized_time_in_force,
    )


def _positive_decimal(raw_value: str, field_name: str) -> Decimal:
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a positive decimal number.") from exc
    if value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return value


def _decimal_to_string(value: Decimal) -> str:
    return format(value.normalize(), "f")
