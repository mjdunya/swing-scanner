"""Run a historical test of the scanner's trend-following setup."""
import json
import math
import os
import signal
import sys
from datetime import datetime

import numpy as np
import yfinance as yf

from config import ATR_TARGET, ATR_STOP, MAX_HOLD_DAYS
from stock_list import get_yahoo_symbols

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def handle_cancel(signum, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, handle_cancel)


def test_symbol(symbol, period="2y"):
    try:
        prices = yf.download(symbol, period=period, auto_adjust=True,
                     progress=False, timeout=10, threads=False)
        if prices is None or len(prices) < 80:
            return []
        if hasattr(prices.columns, "levels"):
            prices.columns = prices.columns.get_level_values(0)
        close = prices["Close"].astype(float)
        high = prices["High"].astype(float)
        low = prices["Low"].astype(float)
        tr = np.maximum(high - low, np.maximum(
            (high - close.shift()).abs(), (low - close.shift()).abs()))
        ma20 = close.rolling(20).mean()
        ma50 = close.rolling(50).mean()
        atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
        trades = []
        hold_days = MAX_HOLD_DAYS["swing"]
        for entry_index in range(50, len(close) - 2):
            if not (close.iloc[entry_index] > ma20.iloc[entry_index] > ma50.iloc[entry_index]):
                continue
            entry = float(close.iloc[entry_index + 1])
            risk = max(float(atr.iloc[entry_index]), entry * 0.02)
            stop = entry - ATR_STOP["swing"] * risk
            target = entry + ATR_TARGET["swing"] * risk
            exit_price = float(close.iloc[min(entry_index + hold_days, len(close) - 1)])
            reason = "time"
            for offset in range(1, min(hold_days, len(close) - entry_index - 1) + 1):
                day_high = float(high.iloc[entry_index + offset])
                day_low = float(low.iloc[entry_index + offset])
                if day_low <= stop:
                    exit_price, reason = stop, "stop"
                    break
                if day_high >= target:
                    exit_price, reason = target, "target"
                    break
            change_pct = (exit_price / entry - 1) * 100
            if math.isfinite(change_pct):
                trades.append({"symbol": symbol, "return_pct": round(change_pct, 2), "exit": reason})
            entry_index += hold_days - 1
        return trades
    except Exception as exc:
        print(f"Skipping {symbol}: {type(exc).__name__}: {exc}", flush=True)
        return []


def normalize_symbol(symbol):
    value = symbol.upper().strip()
    for suffix in (".NS", ".SA", ".SR"):
        if value.endswith(suffix):
            return value[:-len(suffix)]
    return value


def save_results(trades, market, tested_count):
    returns = [trade["return_pct"] for trade in trades]
    winners = [value for value in returns if value > 0]
    losers = [value for value in returns if value <= 0]
    exits = {"target": 0, "stop": 0, "time": 0}
    for trade in trades:
        exits[trade["exit"]] = exits.get(trade["exit"], 0) + 1
    total = len(returns)
    result = {
        "market": market,
        "tested_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "period": "2y",
        "tested_stocks": tested_count,
        "total_trades": total,
        "winning_trades": len(winners),
        "losing_trades": len(losers),
        "win_rate": round(len(winners) / total * 100, 2) if total else 0,
        "expectancy": round(sum(returns) / total, 2) if total else 0,
        "average_win": round(sum(winners) / len(winners), 2) if winners else 0,
        "average_loss": round(sum(losers) / len(losers), 2) if losers else 0,
        "best_trade": round(max(returns), 2) if returns else 0,
        "worst_trade": round(min(returns), 2) if returns else 0,
        "profit_factor": round(sum(winners) / abs(sum(losers)), 2) if losers and sum(losers) else None,
        "exit_breakdown": exits,
        "trades": trades,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"backtest_{market}.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)


def main():
    market = sys.argv[1].lower() if len(sys.argv) > 1 else "india"
    if market not in ("india", "saudi"):
        market = "india"
    symbols = get_yahoo_symbols(market)
    selected = {normalize_symbol(symbol) for symbol in sys.argv[2:] if symbol.strip()}
    if selected:
        symbols = [symbol for symbol in symbols if normalize_symbol(symbol) in selected]
        print(f"🎯 Backtesting {len(symbols)} SELECTED stocks")
    else:
        print(f"🎯 Backtesting ALL {len(symbols)} stocks")
    trades = []
    tested = 0
    try:
        for index, symbol in enumerate(symbols, 1):
            print(f"📥 [{index}/{len(symbols)}] {symbol}", flush=True)
            trades.extend(test_symbol(symbol))
            tested = index
            if index % 10 == 0:
                save_results(trades, market, tested)
                print(f"💾 checkpoint saved ({tested} done)", flush=True)
    finally:
        save_results(trades, market, tested)
        print(f"✅ Saved {tested} stocks scanned so far", flush=True)

    total = len([trade["return_pct"] for trade in trades])
    returns = [trade["return_pct"] for trade in trades]
    print(f"Completed {total} trades; expectancy {round(sum(returns) / total, 2) if total else 0}%/trade")


if __name__ == "__main__":
    main()
