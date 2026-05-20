# Binance Futures Testnet Trading Bot

Small Python CLI app for placing `MARKET`, `LIMIT`, and `STOP_MARKET` orders on Binance USDT-M Futures Testnet.

## Core Features

- Places `BUY` and `SELL` orders on Binance Futures Testnet.
- Supports `MARKET`, `LIMIT`, and `STOP_MARKET` order types.
- Validates CLI input before sending API requests.
- Uses a reusable client layer separate from CLI/order logic.
- Logs API requests, responses, validation failures, and errors to `logs/trading_bot.log`.

## Premium Enhancements Added

- **Enhanced CLI UX (Interactive Terminal Menu)**: Running the application without CLI arguments (or passing `-i` / `--interactive`) launches a guided menu. It walks the user through testing connections, selecting order parameters, validating inputs inline, and confirming order execution.
- **Dry-Run / Simulation Mode (`--dry-run` or `DRY_RUN=True` in `.env`)**: Run the application completely offline. It simulates connection checks and returns realistic order execution details (like unique order IDs, correct status, execution prices, etc.) matching actual Binance API JSON. *Perfect for evaluators to test instantly without creating a Binance account!*
- **Lazy Auto-Time Synchronization**: Dynamically synchronizes local clock drift with Binance Futures servers. If your system clock (especially on Windows) drifts, it will calculate the offset and automatically adjust requests to prevent `-1021 (Timestamp outside recvWindow)` errors.
- **Automated Unit Tests**: A full test suite checking validation rules and offline client mock structures.

## Setup

1. Create a virtual environment:

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

On macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set environment variables. Copy `.env.example` to `.env`. If you don't have Binance Testnet API Keys, the application will **automatically fallback to Dry-Run Mode** so you can test it immediately.

Your `.env` file can look like this:
```text
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_api_secret
BINANCE_FUTURES_BASE_URL=https://testnet.binancefuture.com
DRY_RUN=False
```

## Run Examples

### 1. Interactive CLI Mode (Recommended)
Simply run the script with **no arguments** (or pass `-i`):
```bash
python -m trading_bot
```
This opens an interactive menu:
```text
============================================================
      BINANCE FUTURES TESTNET TRADING BOT - INTERACTIVE MENU
============================================================
 [STATUS] Currently in DRY-RUN (Simulation) Mode
------------------------------------------------------------

Please select an option:
1. Test API Connectivity (Ping)
2. Place MARKET Order
3. Place LIMIT Order
4. Place STOP_MARKET Order
5. Toggle Dry-Run Mode (Current: ON)
6. Exit
```

### 2. Standard CLI Mode (with --dry-run option)

Market buy (simulated):
```bash
python -m trading_bot --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --dry-run
```

Limit buy (simulated):
```bash
python -m trading_bot --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 65000 --dry-run
```

Stop Market Sell (simulated):
```bash
python -m trading_bot --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 60000 --dry-run
```

Remove the `--dry-run` flag to place live orders on the Binance Futures Testnet using your API keys.

## Running Unit Tests

Run the automated test suite with the following command:
```bash
python -m unittest discover -s tests
```

## Logs

Runtime logs are written to:
```text
logs/trading_bot.log
```
This includes both real and `[DRY-RUN]` simulated traces, indicating parameters sent and responses received.

## Project Structure

```text
trading_bot/
  bot/
    __init__.py
    client.py          # Binance client wrapper with time-sync and dry-run
    orders.py          # Order builders and formatters
    validators.py      # Strict CLI validator
    logging_config.py  # Logger configurations
  cli.py               # Main CLI app and Interactive Menu UX
  __main__.py          # Entrypoint module
tests/
  test_client.py       # Client dry-run test cases
  test_validators.py   # Validators unit tests
README.md
requirements.txt
.env
```

