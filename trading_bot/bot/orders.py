from __future__ import annotations

from typing import Any

from trading_bot.bot.client import BinanceFuturesClient
from trading_bot.bot.validators import OrderInput


def build_order_params(order: OrderInput) -> dict[str, str]:
    params = {
        "symbol": order.symbol,
        "side": order.side,
        "type": order.order_type,
        "quantity": order.quantity,
    }
    if order.order_type == "LIMIT":
        params["price"] = order.price or ""
        params["timeInForce"] = order.time_in_force
    elif order.order_type == "STOP_MARKET":
        params["stopPrice"] = order.stop_price or ""
    return params


def place_order(client: BinanceFuturesClient, order: OrderInput) -> dict[str, Any]:
    return client.place_order(build_order_params(order))


def build_order_summary(order: OrderInput) -> str:
    lines = [
        f"  symbol: {order.symbol}",
        f"  side: {order.side}",
        f"  type: {order.order_type}",
        f"  quantity: {order.quantity}",
    ]
    if order.order_type == "LIMIT":
        lines.append(f"  price: {order.price}")
        lines.append(f"  timeInForce: {order.time_in_force}")
    elif order.order_type == "STOP_MARKET":
        lines.append(f"  stopPrice: {order.stop_price}")
    return "\n".join(lines)


def format_order_response(response: dict[str, Any]) -> str:
    details = {
        "orderId": response.get("orderId"),
        "symbol": response.get("symbol"),
        "status": response.get("status"),
        "side": response.get("side"),
        "type": response.get("type"),
        "executedQty": response.get("executedQty"),
        "avgPrice": response.get("avgPrice"),
        "price": response.get("price"),
        "stopPrice": response.get("stopPrice"),
        "origQty": response.get("origQty"),
        "clientOrderId": response.get("clientOrderId"),
    }
    return "\n".join(f"  {key}: {value}" for key, value in details.items() if value is not None)
