from __future__ import annotations

import unittest
from trading_bot.bot.validators import validate_order_input, ValidationError


class TestValidators(unittest.TestCase):
    def test_valid_market_order(self) -> None:
        order = validate_order_input(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity="0.005",
            price=None,
            stop_price=None,
            time_in_force="GTC",
        )
        self.assertEqual(order.symbol, "BTCUSDT")
        self.assertEqual(order.side, "BUY")
        self.assertEqual(order.order_type, "MARKET")
        self.assertEqual(order.quantity, "0.005")
        self.assertIsNone(order.price)
        self.assertIsNone(order.stop_price)

    def test_valid_limit_order(self) -> None:
        order = validate_order_input(
            symbol="ethusdt",  # Test lowercase normalization
            side="sell",      # Test lowercase normalization
            order_type="limit",
            quantity="1.5",
            price="3400.50",
            stop_price=None,
            time_in_force="GTC",
        )
        self.assertEqual(order.symbol, "ETHUSDT")
        self.assertEqual(order.side, "SELL")
        self.assertEqual(order.order_type, "LIMIT")
        self.assertEqual(order.quantity, "1.5")
        self.assertEqual(order.price, "3400.5")

    def test_invalid_symbol(self) -> None:
        with self.assertRaises(ValidationError):
            validate_order_input("BTC", "BUY", "MARKET", "1", None, None, "GTC")

    def test_invalid_side(self) -> None:
        with self.assertRaises(ValidationError):
            validate_order_input("BTCUSDT", "HOLD", "MARKET", "1", None, None, "GTC")

    def test_invalid_order_type(self) -> None:
        with self.assertRaises(ValidationError):
            validate_order_input("BTCUSDT", "BUY", "UNKNOWN", "1", None, None, "GTC")

    def test_missing_price_for_limit(self) -> None:
        with self.assertRaises(ValidationError):
            validate_order_input("BTCUSDT", "BUY", "LIMIT", "1", None, None, "GTC")

    def test_price_with_market(self) -> None:
        with self.assertRaises(ValidationError):
            validate_order_input("BTCUSDT", "BUY", "MARKET", "1", "50000", None, "GTC")

    def test_negative_quantity(self) -> None:
        with self.assertRaises(ValidationError):
            validate_order_input("BTCUSDT", "BUY", "MARKET", "-0.1", None, None, "GTC")

    def test_zero_quantity(self) -> None:
        with self.assertRaises(ValidationError):
            validate_order_input("BTCUSDT", "BUY", "MARKET", "0", None, None, "GTC")


if __name__ == "__main__":
    unittest.main()
