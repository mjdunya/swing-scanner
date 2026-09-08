"""
🌐 DASHBOARD — Flask web server
Usage: python app.py
"""
import math
import os, json, subprocess, sys, threading

# pyright: reportMissingImports=false
from flask import Flask, render_template, request, jsonify  # type: ignore[import-not-found]

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

scan_running = False
backtest_running = False


# ═══════════════════════════════════════════════════════════
# STYLE CONFIG — turns the scanner's flat list into 4 styles
# ═══════════════════════════════════════════════════════════
STYLE_CONFIG = {
    "scalp":      {"max_hold_days": 3,   "stop_mult": 1.0, "target_mult": 1.5, "min_score": 4},
    "swing":      {"max_hold_days": 14,  "stop_mult": 2.0, "target_mult": 3.0, "min_score": 3},
    "positional": {"max_hold_days": 120, "stop_mult": 3.0, "target_mult": 6.0, "min_score": 2},
    "invest":     {"max_hold_days": 365, "stop_mult": 5.0, "target_mult": 10.0, "min_score": 2},
}


def enrich(raw, max_hold_days, stop_mult, target_mult, min_score):
    """Convert raw scanner results into trade-ready cards."""
    out = []
    for r in raw:
        try:
            price = float(r.get("price", 0) or 0)
            chg = float(r.get("change_pct", 0) or 0)
            score = int(r.get("score", 0) or 0)
            if score > 5:                      # scanner uses 0–100 scale now
                score = max(1, round(score / 10))
        except (ValueError, TypeError):
            continue
        if not math.isfinite(price) or not math.isfinite(chg):
            continue
        if price <= 0 or score < min_score:
            continue
        # ATR proxy ~2% of price (we don't have raw candles here)
        atr = max(price * 0.02, 0.5)
        out.append({
            "symbol": r.get("symbol", ""),
            "price": round(price, 2),
            "change_pct": round(chg, 2),
            "rsi": r.get("rsi"),
            "signals": r.get("signals", []),
            "score": score,
            "atr": round(atr, 2),
            "stop": round(price - stop_mult * atr, 2),
            "target": round(price + target_mult * atr, 2),
            "max_hold_days": max_hold_days,
        })
    out.sort(key=lambda x: -x["score"])
    return out


# ═══════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════
def load_data(market):
    path = os.path.join(DATA_DIR, f"scan_{market}.json")
    if not os.path.exists(path) and market == "india":
        legacy = os.path.join(DATA_DIR, "latest_scan.json")
        if os.path.exists(legacy):
            path = legacy

    raw = []
    scanned_at = None
    scanned_count = 0

    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            scanned_at = d.get("scanned_at")
            scanned_count = d.get("scanned_count", 0)
            styles_raw = d.get("styles", {})
            if any(styles_raw.get(k) for k in STYLE_CONFIG):
                return {
                    "scanned_at": scanned_at,
                    "scanned_count": scanned_count,
                    "styles": {
                        k: enrich(styles_raw.get(k, []), **cfg)
                        for k, cfg in STYLE_CONFIG.items()
                    },
                }
            raw = d.get("results", [])
        except Exception as e:
            print(f"⚠️ Could not read {path}: {e}")

    styles = {}
    for style, cfg in STYLE_CONFIG.items():
        styles[style] = enrich(raw, **cfg)

    return {
        "scanned_at": scanned_at,
        "scanned_count": scanned_count,
        "styles": styles,
    }


def load_backtest(market):
    path = os.path.join(DATA_DIR, f"backtest_{market}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"⚠️ Could not read {path}: {exc}")
        return None


def run_job(cmd):
    global scan_running, backtest_running
    try:
        process = subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            env=ENV,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        output = []
        for line in process.stdout or []:
            output.append(line)
            print(line, end="", flush=True)
        returncode = process.wait(timeout=1800)
        if returncode != 0:
            print(f"❌ JOB FAILED (exit code {returncode})")
            print(f"Command: {' '.join(cmd)}")
            if not output:
                print("The scanner returned no output. Check Python dependencies and internet access.")
    except Exception as e:
        print(f"❌ Job crashed: {e}")
    finally:
        scan_running = False
        backtest_running = False

# ═══════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════
@app.route("/")
def index():
    market = request.args.get("market", "india")
    if market not in ("india", "saudi"):
        market = "india"
    data = load_data(market)
    backtest = load_backtest(market)
    styles = data.get("styles", {})
    for k in ("scalp", "swing", "positional", "invest"):
        styles.setdefault(k, [])
    return render_template("index.html", data=data, styles=styles,
                           backtest=backtest, market=market)


@app.route("/api/scan", methods=["POST"])
def api_scan():
    global scan_running
    if scan_running or backtest_running:
        return jsonify({"status": "busy"})
    market = (request.json or {}).get("market", "india").lower()
    if market not in ("india", "saudi"):
        market = "india"
    scan_running = True
    threading.Thread(
        target=run_job,
        args=([sys.executable, os.path.join(BASE_DIR, "scanner.py"), market],),
        daemon=True,
    ).start()
    return jsonify({"status": "started"})


@app.route("/api/backtest", methods=["POST"])
def api_backtest():
    global backtest_running
    if scan_running or backtest_running:
        return jsonify({"status": "busy"})
    market = (request.json or {}).get("market", "india").lower()
    if market not in ("india", "saudi"):
        market = "india"
    backtester = os.path.join(BASE_DIR, "backtester.py")
    if not os.path.exists(backtester):
        return jsonify({"status": "unavailable"}), 503
    backtest_running = True
    threading.Thread(
        target=run_job,
        args=([sys.executable, backtester, market],),
        daemon=True,
    ).start()
    return jsonify({"status": "started"})


@app.route("/api/status")
def api_status():
    return jsonify({"scan_running": scan_running, "backtest_running": backtest_running})


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    port = int(os.environ.get("PORT", "5000"))
    print(f"\n🌐 Dashboard → http://127.0.0.1:{port}")
    app.run(debug=False, use_reloader=False, host="0.0.0.0", port=port)
