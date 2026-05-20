from __future__ import annotations

import unittest
from trading_bot.bot.client import BinanceFuturesClient, BinanceAPIError


class TestBinanceFuturesClient(unittest.TestCase):
    def setUp(self) -> None:
        self.client = BinanceFuturesClient(
            api_key="dummy_key",
            api_secret="dummy_secret",
            dry_run=True,
        )

    def test_dry_run_ping(self) -> None:
        # Pinging in dry-run should not throw an error and return mock account details
        res = self.client.ping()
        self.assertTrue(res["canTrade"])
        self.assertEqual(res["totalWalletBalance"], "10000.00000000")

    def test_dry_run_market_order(self) -> None:
        params = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "MARKET",
            "quantity": "0.05",
        }
        res = self.client.place_order(params)
        self.assertEqual(res["symbol"], "BTCUSDT")
        self.assertEqual(res["status"], "FILLED")
        self.assertEqual(res["executedQty"], "0.05")
        self.assertEqual(res["side"], "BUY")
        self.assertEqual(res["type"], "MARKET")
        self.assertIsNotNone(res["orderId"])

    def test_dry_run_limit_order(self) -> None:
        params = {
            "symbol": "ETHUSDT",
            "side": "SELL",
            "type": "LIMIT",
            "quantity": "1.2",
            "price": "3450.00",
            "timeInForce": "GTC",
        }
        res = self.client.place_order(params)
        self.assertEqual(res["symbol"], "ETHUSDT")
        self.assertEqual(res["status"], "NEW")
        self.assertEqual(res["executedQty"], "0")
        self.assertEqual(res["price"], "3450.00")
        self.assertEqual(res["side"], "SELL")
        self.assertEqual(res["type"], "LIMIT")

    def test_dry_run_unknown_endpoint(self) -> None:
        with self.assertRaises(BinanceAPIError):
            self.client._signed_request("GET", "/fapi/v1/invalid_path", {})


if __name__ == "__main__":
    unittest.main()
