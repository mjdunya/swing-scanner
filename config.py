"""
⚙️ CONFIG — Swing Scanner Pro
"""

# ── 📥 Data ──
LOOKBACK_DAYS = 500

# ── 🚫 Filters ──
MIN_PRICE = 20
MIN_VOLUME = 100000

# ── 📊 Signal switches ──
USE_BREAKOUT = True
USE_MACD = True
USE_RSI = True
RSI_OVERSOLD = 35
USE_MA_TREND = True
VOLUME_SPIKE_MULT = 1.5

# ── 📐 ATR stops & targets ──
ATR_PERIOD = 14
ATR_STOP = {"scalp": 1.0, "swing": 2.0, "positional": 2.5, "invest": 3.0}
ATR_TARGET = {"scalp": 2.0, "swing": 4.0, "positional": 100, "invest": 100}  # ≥100 = trail

# ── ⏳ Max holding period (days) ──
MAX_HOLD_DAYS = {"scalp": 3, "swing": 12, "positional": 120, "invest": 365}

# ── 🔝 Results ──
TOP_N_PER_STYLE = 6
