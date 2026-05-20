from __future__ import annotations

import hashlib
import hmac
import json
import os
import random
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests

from trading_bot.bot.logging_config import get_logger


class BinanceAPIError(Exception):
    """Raised when Binance returns an API error response."""


@dataclass
class BinanceFuturesClient:
    api_key: str
    api_secret: str
    base_url: str = os.getenv("BINANCE_FUTURES_BASE_URL", "https://testnet.binancefuture.com")
    recv_window: int = 5000
    timeout: int = 10
    dry_run: bool = False
    sync_time: bool = True

    def __post_init__(self) -> None:
        self.base_url = self.base_url.strip().rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self.api_key,
            }
        )
        self._logger = get_logger(__name__)
        self._time_offset = None

    def place_order(self, order_params: dict[str, Any]) -> dict[str, Any]:
        return self._signed_request("POST", "/fapi/v1/order", order_params)

    def public_ping(self) -> None:
        """Unsigned request to check basic connectivity and URL validity."""
        if self.dry_run:
            self._logger.info("[DRY-RUN] Intercepted public_ping request.")
            return
        url = f"{self.base_url}/fapi/v1/ping"
        resp = self._session.get(url, timeout=self.timeout)
        resp.raise_for_status()

    def get_server_time(self) -> int:
        if self.dry_run:
            return int(time.time() * 1000)
        url = f"{self.base_url}/fapi/v1/time"
        resp = self._session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()["serverTime"]

    def ping(self) -> dict[str, Any]:
        self.public_ping()  # Check network first
        return self._signed_request("GET", "/fapi/v2/account", {})

    def _signed_request(self, method: str, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if self.dry_run:
            return self._handle_dry_run(method, path, params)

        # Lazy server time synchronization
        if self.sync_time and self._time_offset is None:
            try:
                server_time = self.get_server_time()
                local_time = int(time.time() * 1000)
                self._time_offset = server_time - local_time
                self._logger.info("Synchronized time with Binance Futures server. Offset: %dms", self._time_offset)
            except Exception as exc:
                self._logger.warning("Failed to synchronize time with Binance: %s. Using local time.", exc)
                self._time_offset = 0

        offset = self._time_offset or 0
        request_params = {
            **params,
            "recvWindow": self.recv_window,
            "timestamp": int(time.time() * 1000) + offset,
        }
        query_string = urlencode(request_params, doseq=True)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        signed_params = {**request_params, "signature": signature}
        url = f"{self.base_url}{path}"

        self._logger.info(
            "API request %s %s params=%s",
            method,
            path,
            json.dumps(self._redact_for_log(request_params), sort_keys=True),
        )

        try:
            headers = {}
            if method.upper() == "POST":
                # Explicitly set for POST, though requests usually handles dict data correctly
                headers["Content-Type"] = "application/x-www-form-urlencoded"

            response = self._session.request(
                method=method,
                url=url,
                params=signed_params if method.upper() == "GET" else None,
                data=signed_params if method.upper() != "GET" else None,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            self._logger.error("API request timeout %s %s: %s", method, path, exc)
            raise TimeoutError(str(exc)) from exc
        except requests.RequestException as exc:
            self._logger.error("API request failed %s %s: %s", method, path, exc)
            raise OSError(str(exc)) from exc

        self._logger.info(
            "API response status=%s body=%s",
            response.status_code,
            self._truncate(response.text),
        )

        # Monitor API Weight Usage
        used_weight = response.headers.get("X-MBX-USED-WEIGHT-1M")
        if used_weight and int(used_weight) > 1200:  # Threshold for warning
            self._logger.warning("Approaching API rate limit. Current weight: %s", used_weight)

        try:
            payload = response.json()
        except ValueError as exc:
            raise BinanceAPIError(f"Non-JSON response from Binance: {response.text[:300]}") from exc

        if response.status_code >= 400:
            code = payload.get("code", response.status_code)
            message = payload.get("msg", payload)
            raise BinanceAPIError(f"{code}: {message}")

        return payload

    def _handle_dry_run(self, method: str, path: str, params: dict[str, Any]) -> dict[str, Any]:
        self._logger.info(
            "[DRY-RUN] Intercepted %s %s request with params: %s",
            method,
            path,
            json.dumps(self._redact_for_log(params), sort_keys=True),
        )
        time.sleep(0.1)  # Simulate network latency

        if path in ("/fapi/v2/account", "/fapi/v1/account"):
            # Account ping
            mock_resp = {
                "canDeposit": True,
                "canTrade": True,
                "canWithdraw": True,
                "feeTier": 0,
                "maxWithdrawAmount": "999999",
                "updateTime": int(time.time() * 1000),
                "totalInitialMargin": "0.00000000",
                "totalMaintMargin": "0.00000000",
                "totalWalletBalance": "10000.00000000",
                "totalMarginBalance": "10000.00000000",
                "assets": [
                    {
                        "asset": "USDT",
                        "walletBalance": "10000.00000000",
                        "unrealizedProfit": "0.00000000",
                        "marginBalance": "10000.00000000",
                        "maintMargin": "0.00000000",
                        "initialMargin": "0.00000000",
                    }
                ],
                "positions": []
            }
            self._logger.info("[DRY-RUN] Response: status=200 body=%s", json.dumps(mock_resp))
            return mock_resp

        elif path == "/fapi/v1/order":
            order_type = params.get("type", "MARKET")
            side = params.get("side", "BUY")
            symbol = params.get("symbol", "BTCUSDT")
            quantity = params.get("quantity", "0.001")
            
            # Formulate simulated average prices depending on the symbol
            price_map = {"BTCUSDT": 67000.0, "ETHUSDT": 3450.0, "BNBUSDT": 580.0}
            base_price = price_map.get(symbol.upper(), 100.0)
            
            # Slight random wiggle in simulated execution price
            wiggle = random.uniform(-0.001, 0.001)
            simulated_price = base_price * (1 + wiggle)

            order_id = random.randint(1000000000, 9999999999)
            client_order_id = f"dry_run_{int(time.time()*1000)}"

            if order_type == "MARKET":
                executed_qty = quantity
                avg_price = f"{simulated_price:.2f}"
                status = "FILLED"
                price = "0.00"
            elif order_type == "LIMIT":
                executed_qty = "0"
                avg_price = "0.00"
                status = "NEW"
                price = params.get("price", f"{base_price:.2f}")
            else:  # STOP_MARKET or other
                executed_qty = "0"
                avg_price = "0.00"
                status = "NEW"
                price = "0.00"

            mock_resp = {
                "orderId": order_id,
                "symbol": symbol,
                "status": status,
                "clientOrderId": client_order_id,
                "price": price,
                "avgPrice": avg_price,
                "origQty": quantity,
                "executedQty": executed_qty,
                "side": side,
                "type": order_type,
                "timeInForce": params.get("timeInForce", "GTC"),
                "stopPrice": params.get("stopPrice", "0.00") if "stopPrice" in params else None,
                "updateTime": int(time.time() * 1000)
            }
            # Clean None values
            mock_resp = {k: v for k, v in mock_resp.items() if v is not None}
            self._logger.info("[DRY-RUN] Response: status=200 body=%s", json.dumps(mock_resp))
            return mock_resp

        else:
            raise BinanceAPIError(f"-5000: Endpoint {path} not mocked in dry-run mode.")


    @staticmethod
    def _redact_for_log(params: dict[str, Any]) -> dict[str, Any]:
        sensitive_keys = {"signature", "api_key", "apikey"}
        redacted = params.copy()
        for key in redacted:
            if key.lower() in sensitive_keys:
                redacted[key] = "<REDACTED>"
        return redacted

    @staticmethod
    def _truncate(value: str, limit: int = 2000) -> str:
        if len(value) <= limit:
            return value
        return f"{value[:limit]}...<truncated>"
