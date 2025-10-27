import os, json, datetime
from polygon import RESTClient
from flask import Flask, request, jsonify

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "../data/state.json")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

def load_state():
    if not os.path.exists(DATA_FILE):
        return {"portfolio": [], "closed_trades": [], "scan_history": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(DATA_FILE, "w") as f:
        json.dump(state, f, indent=2)

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d for d in deltas if d > 0]
    losses = [-d for d in deltas if d < 0]
    avg_gain = sum(gains[-period:]) / period if gains else 0
    avg_loss = sum(losses[-period:]) / period if losses else 1e-10
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

@app.route("/scan", methods=["POST"])
def balanced_swing_scan():
    body = request.get_json()
    date = body.get("date", datetime.date.today().isoformat())
    universe = body.get("universe", "SP500")

    client = RESTClient(api_key=POLYGON_API_KEY)
    tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "NFLX"]

    qualified = []
    for t in tickers:
        try:
            bars = client.get_aggs(t, 1, "day", "2024-06-01", date)
            closes = [b.close for b in bars]
            if len(closes) < 200:
                continue
            price = closes[-1]
            dma_20 = sum(closes[-20:]) / 20
            dma_50 = sum(closes[-50:]) / 50
            dma_200 = sum(closes[-200:]) / 200
            rsi = calc_rsi(closes)
            if dma_50 < price < dma_20 and 40 <= rsi <= 55:
                qualified.append({
                    "ticker": t,
                    "price": price,
                    "rsi": rsi,
                    "dma_20": dma_20,
                    "dma_50": dma_50,
                    "dma_200": dma_200
                })
        except Exception as e:
            print(f"Error scanning {t}: {e}")

    state = load_state()
    state["scan_history"].append({
        "scan_date": date,
        "qualified_candidates": qualified
    })
    save_state(state)
    return jsonify({"scan_date": date, "qualified": qualified})

@app.route("/state", methods=["GET"])
def get_state():
    return jsonify(load_state())

if __name__ == "__main__":
    app.run()
