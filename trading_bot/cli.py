from __future__ import annotations

import argparse
import os
import sys
import time
from dotenv import load_dotenv

from trading_bot.bot.client import BinanceAPIError, BinanceFuturesClient
from trading_bot.bot.logging_config import configure_logging, get_logger
from trading_bot.bot.orders import build_order_summary, format_order_response, place_order
from trading_bot.bot.validators import ValidationError, validate_order_input


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Place MARKET, LIMIT, and STOP_MARKET orders on Binance Futures Testnet.",
    )
    parser.add_argument("--symbol", help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", help="BUY or SELL")
    parser.add_argument("--type", dest="order_type", help="MARKET, LIMIT, or STOP_MARKET")
    parser.add_argument("--quantity", help="Order quantity, e.g. 0.001")
    parser.add_argument("--price", help="Limit price. Required for LIMIT orders.")
    parser.add_argument("--stop-price", help="Stop price. Required for STOP_MARKET orders.")
    parser.add_argument(
        "--time-in-force",
        default="GTC",
        choices=["GTC", "IOC", "FOK", "GTX"],
        help="Time in force for LIMIT orders. Default: GTC",
    )
    parser.add_argument(
        "--ping",
        action="store_true",
        help="Test API connectivity and key validity without placing an order.",
    )
    parser.add_argument(
        "--recv-window",
        type=int,
        default=5000,
        help="Binance recvWindow in milliseconds. Default: 5000",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run simulation mode without making actual requests to Binance Futures.",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Launch the interactive terminal menu.",
    )
    return parser


def run_interactive_mode(logger, api_key: str, api_secret: str, recv_window: int, is_dry_run_init: bool) -> int:
    dry_run = is_dry_run_init
    
    print("\n" + "=" * 60)
    print("      BINANCE FUTURES TESTNET TRADING BOT - INTERACTIVE MENU")
    print("=" * 60)
    if dry_run:
        print(" [STATUS] Currently in DRY-RUN (Simulation) Mode")
    else:
        print(" [STATUS] Currently in REAL API Mode (Warning: Active Orders!)")
    print("-" * 60)
    
    while True:
        print("\nPlease select an option:")
        print("1. Test API Connectivity (Ping)")
        print("2. Place MARKET Order")
        print("3. Place LIMIT Order")
        print("4. Place STOP_MARKET Order")
        print(f"5. Toggle Dry-Run Mode (Current: {'ON' if dry_run else 'OFF'})")
        print("6. Exit")
        
        try:
            choice = input("\nEnter choice (1-6): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting interactive mode. Goodbye!")
            return 0

        if choice == "6":
            print("Exiting interactive mode. Goodbye!")
            return 0
        
        elif choice == "5":
            dry_run = not dry_run
            print(f"Dry-run mode is now: {'ON' if dry_run else 'OFF'}")
            continue
            
        elif choice == "1":
            print("\n--- Testing API Connectivity ---")
            client = BinanceFuturesClient(
                api_key=api_key if not dry_run else "mock_key",
                api_secret=api_secret if not dry_run else "mock_secret",
                recv_window=recv_window,
                dry_run=dry_run,
            )
            try:
                print("Testing public connectivity...")
                client.public_ping()
                server_time = client.get_server_time()
                local_time = int(time.time() * 1000)
                diff = abs(server_time - local_time)
                print(f"Server time check: offset is {diff}ms")
                print("Testing signed authentication...")
                client.ping()
                print("\nSuccess: API connectivity test passed.")
            except Exception as exc:
                print(f"\nFailure: API connectivity test failed: {exc}", file=sys.stderr)
            continue
            
        elif choice in ("2", "3", "4"):
            order_type = "MARKET" if choice == "2" else ("LIMIT" if choice == "3" else "STOP_MARKET")
            print(f"\n--- Place {order_type} Order ---")
            
            # Prompts with input validation
            symbol = ""
            while not symbol:
                symbol = input("Enter Trading Symbol (e.g. BTCUSDT) [BTCUSDT]: ").strip().upper()
                if not symbol:
                    symbol = "BTCUSDT"
            
            side = ""
            while side not in ("BUY", "SELL"):
                side = input("Enter Side (BUY/SELL): ").strip().upper()
                if side not in ("BUY", "SELL"):
                    print("Error: Side must be BUY or SELL.")
            
            quantity = ""
            while not quantity:
                quantity = input("Enter Quantity (e.g. 0.001): ").strip()
                if not quantity:
                    print("Error: Quantity is required.")
            
            price = None
            if order_type == "LIMIT":
                while not price:
                    price = input("Enter Limit Price: ").strip()
                    if not price:
                        print("Error: Price is required for LIMIT orders.")
            
            stop_price = None
            if order_type == "STOP_MARKET":
                while not stop_price:
                    stop_price = input("Enter Stop Trigger Price: ").strip()
                    if not stop_price:
                        print("Error: Stop price is required for STOP_MARKET orders.")
            
            time_in_force = "GTC"
            if order_type == "LIMIT":
                tif_input = input("Enter Time In Force (GTC, IOC, FOK, GTX) [GTC]: ").strip().upper()
                if tif_input in ("GTC", "IOC", "FOK", "GTX"):
                    time_in_force = tif_input

            # Confirm placement
            print("\nOrder Summary:")
            print(f"  Symbol: {symbol}")
            print(f"  Side: {side}")
            print(f"  Type: {order_type}")
            print(f"  Quantity: {quantity}")
            if price:
                print(f"  Price: {price}")
            if stop_price:
                print(f"  Stop Price: {stop_price}")
            print(f"  Time in Force: {time_in_force}")
            print(f"  Mode: {'DRY-RUN (Simulated)' if dry_run else 'REAL API'}")
            
            confirm = input("\nDo you want to submit this order? (y/n) [y]: ").strip().lower()
            if confirm and confirm not in ("y", "yes"):
                print("Order cancelled.")
                continue
                
            try:
                order_input = validate_order_input(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                    stop_price=stop_price,
                    time_in_force=time_in_force,
                )
            except ValidationError as exc:
                print(f"Validation Error: {exc}", file=sys.stderr)
                continue
                
            client = BinanceFuturesClient(
                api_key=api_key if not dry_run else "mock_key",
                api_secret=api_secret if not dry_run else "mock_secret",
                recv_window=recv_window,
                dry_run=dry_run,
            )
            
            print("\nSubmitting order...")
            try:
                response = place_order(client, order_input)
                print("\nOrder response details:")
                print(format_order_response(response))
                print("\nSuccess: order completed successfully.")
            except Exception as exc:
                print(f"\nFailure: order placement failed: {exc}", file=sys.stderr)
                
        else:
            print("Invalid choice. Please select 1 to 6.")


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    configure_logging()
    logger = get_logger(__name__)
    parser = build_parser()
    args = parser.parse_args(argv)

    api_key = (os.getenv("BINANCE_API_KEY") or "").strip()
    api_secret = (os.getenv("BINANCE_API_SECRET") or "").strip()
    env_dry_run = os.getenv("DRY_RUN", "false").strip().lower() in ("true", "1", "yes")
    
    # Auto dry-run if explicitly requested or if environment config says so or keys are empty
    is_dry_run = args.dry_run or env_dry_run or not api_key or not api_secret

    # Check if we should launch interactive mode
    # Launch if --interactive is passed OR if the script is run with NO CLI arguments (i.e. sys.argv has length 1 and argv is None)
    is_no_args = (len(sys.argv) == 1 and argv is None)
    if args.interactive or is_no_args:
        if is_dry_run and (not api_key or not api_secret):
            print("Note: API keys not configured in .env. Running interactive mode in DRY-RUN mode.")
        elif is_dry_run:
            print("Note: Running interactive mode in DRY-RUN mode as requested.")
        return run_interactive_mode(logger, api_key, api_secret, args.recv_window, is_dry_run)

    if not is_dry_run and (not api_key or not api_secret):
        message = "Missing BINANCE_API_KEY or BINANCE_API_SECRET environment variable. To test offline, pass --dry-run."
        logger.error(message)
        print(f"\nFailure: {message}", file=sys.stderr)
        return 2

    if args.ping:
        if is_dry_run:
            print("Note: Running connectivity test in DRY-RUN (simulation) mode.")
        else:
            print(f"Debug: Loaded API Key (masked): {api_key[:4]}...{api_key[-4:]}", file=sys.stderr)

        client = BinanceFuturesClient(
            api_key=api_key if not is_dry_run else "mock_key",
            api_secret=api_secret if not is_dry_run else "mock_secret",
            recv_window=args.recv_window,
            dry_run=is_dry_run,
        )
        try:
            print("Testing public connectivity...")
            client.public_ping()

            server_time = client.get_server_time()
            local_time = int(time.time() * 1000)
            diff = abs(server_time - local_time)
            print(f"Server time sync check: offset is {diff}ms")
            if diff > 5000 and not is_dry_run:
                print(f"Warning: Local clock is out of sync by {diff}ms. Auto-time-sync will correct this during execution.")

            print("Testing signed authentication...")
            client.ping()
            print("\nSuccess: API connectivity test passed. Your API keys are valid and permissions seem correct.")
            return 0
        except BinanceAPIError as exc:
            logger.error("Binance API error during ping test: %s", exc)
            print(f"\nFailure: Authentication failed: {exc}", file=sys.stderr)
            if "-2015" in str(exc):
                print("Tips to resolve -2015 error during ping test:")
                print("  1. Ensure your keys were generated at https://testnet.binancefuture.com")
                print("  2. Check that 'Enable Futures' is active for this API key on Binance Testnet.")
                print("  3. If you have IP restrictions, ensure your current public IP is whitelisted.")
                print("  4. Try generating a new API key pair on Testnet and updating your .env file.")
            return 1
        except Exception as exc:
            logger.exception("Unexpected error during ping test")
            print(f"\nFailure: API connectivity test failed: {exc}", file=sys.stderr)
            return 1

    # If we reached here, we are placing an order. Ensure mandatory fields exist.
    if not all([args.symbol, args.side, args.order_type, args.quantity]):
        parser.error("the following arguments are required for order placement: --symbol, --side, --type, --quantity")

    try:
        order = validate_order_input(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
            time_in_force=args.time_in_force,
        )
    except ValidationError as exc:
        logger.warning("Validation failed: %s", exc)
        print(f"Validation error: {exc}", file=sys.stderr)
        return 2

    print("Order request summary")
    print(build_order_summary(order))
    if is_dry_run:
        print("Note: Placing order in DRY-RUN (simulated) mode.")

    client = BinanceFuturesClient(
        api_key=api_key if not is_dry_run else "mock_key",
        api_secret=api_secret if not is_dry_run else "mock_secret",
        recv_window=args.recv_window,
        dry_run=is_dry_run,
    )

    try:
        response = place_order(client, order)
    except BinanceAPIError as exc:
        logger.exception("Binance API error while placing order")
        if "-2015" in str(exc):
            print("\nFailure: Binance API error: -2015 (Invalid API-key, IP, or permissions).")
            print("Tips to resolve:")
            print("  1. Ensure your keys were generated at https://testnet.binancefuture.com")
            print("  2. Check that 'Enable Futures' is active for this API key.")
            print("  3. If you just created the key, wait a minute and try again.")
            return 1
        print(f"\nFailure: Binance API error: {exc}", file=sys.stderr)
        return 1
    except TimeoutError as exc:
        logger.exception("Network timeout while placing order")
        print(f"\nFailure: network timeout: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        logger.exception("Network error while placing order")
        print(f"\nFailure: network error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.exception("Unexpected error while placing order")
        print(f"\nFailure: unexpected error: {exc}", file=sys.stderr)
        return 1

    print("\nOrder response details")
    print(format_order_response(response))
    print("\nSuccess: order request submitted to Binance Futures Testnet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

