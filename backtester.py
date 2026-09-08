"""
🌐 DASHBOARD — Flask web server
Usage: python app.py
"""
import os, json, subprocess, sys, threading
import importlib

try:
    _flask = importlib.import_module("flask")
except ImportError as exc:
    raise ImportError("Flask is required. Install it with: python -m pip install Flask") from exc

Flask = _flask.Flask
render_template = _flask.render_template
request = _flask.request
jsonify = _flask.jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

scan_running = False
backtest_running = False


def load_data(market):
    path = os.path.join(DATA_DIR, f"scan_{market}.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Could not read {path}: {e}")
    return {"scanned_at": None, "scanned_count": 0,
            "styles": {"scalp": [], "swing": [], "positional": [], "invest": []}}


def load_backtest(market):
    path = os.path.join(DATA_DIR, f"backtest_{market}.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def run_job(cmd):
    """Run scanner.py in background, print real errors on failure."""
    global scan_running, backtest_running
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=1800, cwd=BASE_DIR,
        )
        if result.returncode != 0:
            print("❌ JOB FAILED — output:")
            print(result.stdout[-3000:])
            print(result.stderr[-3000:])
        else:
            print(result.stdout[-1500:])
    except Exception as e:
        print(f"❌ Job crashed: {e}")
    finally:
        scan_running = False
        backtest_running = False


@app.route("/")
def index():
    market = request.args.get("market", "india")
    data = load_data(market)
    backtest = load_backtest(market)
    styles = data.get("styles", {})
    # Guarantee all 4 keys exist
    for k in ("scalp", "swing", "positional", "invest"):
        styles.setdefault(k, [])
    return render_template("index.html", data=data, styles=styles,
                           backtest=backtest, market=market)


@app.route("/api/scan", methods=["POST"])
def api_scan():
    global scan_running
    if scan_running or backtest_running:
        return jsonify({"status": "busy"})
    market = (request.json or {}).get("market", "india")
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
    market = (request.json or {}).get("market", "india")
    backtest_running = True
    threading.Thread(
        target=run_job,
        args=([sys.executable, os.path.join(BASE_DIR, "backtest.py"), market],),
        daemon=True,
    ).start()
    return jsonify({"status": "started"})


@app.route("/api/status")
def api_status():
    return jsonify({"scan_running": scan_running, "backtest_running": backtest_running})


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    print("\n🌐 Dashboard → http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=5000)
