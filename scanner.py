"""
🔍 SCANNER — analyzes stocks & saves results per style
Usage: python scanner.py india   (or 'saudi')
"""
import math
import sys, json, os
from datetime import datetime

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
import yfinance as yf  # type: ignore[import-not-found]
import pandas as pd  # type: ignore[import-not-found]
import numpy as np  # type: ignore[import-not-found]

from config import (
    LOOKBACK_DAYS, MIN_PRICE, MIN_VOLUME,
    USE_BREAKOUT, USE_MACD, USE_RSI, RSI_OVERSOLD, USE_MA_TREND,
    VOLUME_SPIKE_MULT, ATR_PERIOD, ATR_STOP, ATR_TARGET,
    MAX_HOLD_DAYS, TOP_N_PER_STYLE,
)
from stock_list import get_yahoo_symbols

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ═══════════ INDICATORS ═══════════

def add_indicators(df):
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["VolAvg20"] = df["Volume"].rolling(20).mean()

    # RSI (Wilder)
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # ATR
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1/ATR_PERIOD, adjust=False).mean()

    df["High52w"] = df["Close"].rolling(min(252, len(df))).max()
    return df


def analyze(symbol):
    try:
        tkr = yf.Ticker(symbol)
        df = tkr.history(
            period=f"{LOOKBACK_DAYS}d", auto_adjust=True, timeout=20
        )
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df is None:
            print(f"   ⚠️ {symbol}: no usable price history", flush=True)
            return None
        df = df.dropna(subset=["Close", "High", "Low", "Volume"])
        if len(df) < 60:
            print(f"   ⚠️ {symbol}: no usable price history", flush=True)
            return None

        df = add_indicators(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        price = float(last["Close"])

        if price < MIN_PRICE:
            return None
        vol = float(last["Volume"])
        vol_avg = float(last["VolAvg20"]) if not np.isnan(last["VolAvg20"]) else 0
        if vol_avg < MIN_VOLUME:
            return None

        atr = float(last["ATR"]) if not np.isnan(last["ATR"]) else price * 0.02
        if atr <= 0:
            atr = price * 0.02

        change_pct = (price / float(prev["Close"]) - 1) * 100
        if not all(math.isfinite(value) for value in (price, atr, change_pct)):
            print(f"   ⚠️ {symbol}: invalid numeric data — skipped", flush=True)
            return None

        # ═══ Signals ═══
        signals = []
        score = 0

        h52 = float(last["High52w"]) if not np.isnan(last["High52w"]) else price
        if USE_BREAKOUT and h52 > 0 and price >= h52 * 0.95:
            signals.append("🚀 Near 52-week high breakout")
            score += 25

        if USE_MACD and not np.isnan(last["MACD"]) and not np.isnan(last["MACD_Signal"]):
            if last["MACD"] > last["MACD_Signal"] and prev["MACD"] <= prev["MACD_Signal"]:
                signals.append("📈 MACD bullish crossover")
                score += 20
            elif last["MACD"] > last["MACD_Signal"]:
                signals.append("📊 MACD above signal line")
                score += 10

        rsi = float(last["RSI"]) if not np.isnan(last["RSI"]) else 50
        if USE_RSI:
            if rsi < RSI_OVERSOLD:
                signals.append(f"💎 RSI oversold ({rsi:.0f}) — rebound zone")
                score += 15
            elif 50 <= rsi <= 65:
                signals.append(f"💪 RSI healthy momentum ({rsi:.0f})")
                score += 10

        if USE_MA_TREND and not np.isnan(last["MA50"]):
            if not np.isnan(last["MA200"]) and price > last["MA50"] > last["MA200"]:
                signals.append("🏗️ Strong uptrend (above MA50 & MA200)")
                score += 20
            elif price > last["MA50"]:
                signals.append("📊 Above 50-day average")
                score += 10

        if vol_avg > 0 and vol > vol_avg * VOLUME_SPIKE_MULT:
            signals.append(f"🔥 Volume spike ({vol/vol_avg:.1f}x average)")
            score += 15

        if not np.isnan(last["MA20"]) and not np.isnan(last["MA50"]):
            if price > last["MA20"] > last["MA50"]:
                signals.append("✨ Perfect MA alignment (Price > MA20 > MA50)")
                score += 10

        if not signals or score < 20:
            return None

        return {
            "symbol": symbol,
            "price": round(price, 2),
            "atr": round(atr, 2),
            "score": score,
            "change_pct": round(change_pct, 2),
            "signals": signals,
        }

    except Exception as e:
        print(f"   ⚠️ {symbol}: {type(e).__name__}: {e} — skipped", flush=True)
        return None


def main():
    market = sys.argv[1] if len(sys.argv) > 1 else "india"
    stocks = get_yahoo_symbols(market)
    total = len(stocks)

    print(f"\n{'='*55}")
    print(f"🔍 SCANNING {market.upper()} — {total} stocks")
    print(f"{'='*55}\n")

    raw = []
    for i, sym in enumerate(stocks, 1):
        print(f"📥 [{i}/{total}] {sym} ...", flush=True)
        r = analyze(sym)
        if r:
            print(f"   ✅ {r['symbol']} score {r['score']} — {r['signals'][0]}")
            raw.append(r)

    print(f"\n📊 {len(raw)} stocks with signals")

    # ═══ Split into styles ═══
    styles = {"scalp": [], "swing": [], "positional": [], "invest": []}

    for r in raw:
        atr_pct = r["atr"] / r["price"] * 100
        if r["score"] >= 70 and atr_pct < 3.5:
            styles["invest"].append(dict(r,
                stop=round(r["price"] - ATR_STOP["invest"] * r["atr"], 2),
                target=round(r["price"] + 8 * r["atr"], 2),
                max_hold_days=MAX_HOLD_DAYS["invest"]))
        if 40 <= r["score"] < 95 and atr_pct < 4:
            styles["positional"].append(dict(r,
                stop=round(r["price"] - ATR_STOP["positional"] * r["atr"], 2),
                target=None,
                max_hold_days=MAX_HOLD_DAYS["positional"]))
        if r["score"] >= 45:
            styles["swing"].append(dict(r,
                stop=round(r["price"] - ATR_STOP["swing"] * r["atr"], 2),
                target=round(r["price"] + ATR_TARGET["swing"] * r["atr"], 2),
                max_hold_days=MAX_HOLD_DAYS["swing"]))
        if r["score"] >= 55 and atr_pct >= 1.2:
            styles["scalp"].append(dict(r,
                stop=round(r["price"] - ATR_STOP["scalp"] * r["atr"], 2),
                target=round(r["price"] + ATR_TARGET["scalp"] * r["atr"], 2),
                max_hold_days=MAX_HOLD_DAYS["scalp"]))

    for k in styles:
        styles[k].sort(key=lambda x: x["score"], reverse=True)
        styles[k] = styles[k][:TOP_N_PER_STYLE]
        print(f"   {k}: {len(styles[k])} setups")

    # ═══ Save ═══
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    data = {
        "market": market,
        "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "scanned_count": total,
        "results": raw,
        "styles": styles,
    }
    path = os.path.join(BASE_DIR, "data", f"scan_{market}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Results saved → {path}")
    print("🎯 Done! Run 'python app.py' and open http://127.0.0.1:5000\n")


if __name__ == "__main__":
    main()
