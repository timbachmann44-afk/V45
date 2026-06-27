import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="V43 REAL MARKET ENGINE", layout="wide")

st.title("🚀 V43 REAL MARKET ENGINE")

API_KEY = st.secrets.get("TWELVE_DATA_API_KEY", None)

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

# =========================
# DARK MODE
# =========================
st.markdown("""
<style>

.stApp {
    background:#05070D;
    color:#EAEAEA;
}

h1,h2,h3 {
    color:#00E5FF;
}

.card {
    background:#0B1220;
    padding:14px;
    border-radius:14px;
    margin-bottom:12px;
    border:1px solid #1f2937;
}

.buy {
    border-left:5px solid #00FF88;
}

.sell {
    border-left:5px solid #FF3B3B;
}

</style>
""", unsafe_allow_html=True)

# =========================
# COINS
# =========================
coins = ["BTC/USD","ETH/USD","XRP/USD","SOL/USD","ADA/USD","DOGE/USD","BNB/USD"]

selected = st.sidebar.multiselect("Coins", coins, default=coins)

# =========================
# DATA LOADER
# =========================
@st.cache_data(ttl=30)
def load_data(symbol):

    if not API_KEY:
        return None

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": symbol,
        "interval": "15min",
        "outputsize": 200,
        "apikey": API_KEY
    }

    try:
        r = requests.get(url, params=params, timeout=10).json()

        if "values" not in r:
            return None

        df = pd.DataFrame(r["values"])
        df = df.iloc[::-1]

        for c in ["open","high","low","close"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df

    except:
        return None

# =========================
# REAL MARKET STRUCTURE (FIX)
# =========================
def structure(df):

    price = df["close"].iloc[-1]

    # 🔥 adaptive (NOT fixed 25 rolling extremes)
    window = 15

    support = df["low"].rolling(window).min().iloc[-1]
    resistance = df["high"].rolling(window).max().iloc[-1]

    atr = (df["high"] - df["low"]).rolling(window).mean().iloc[-1]

    return price, support, resistance, atr

# =========================
# V43 ENGINE (REAL MARKET BEHAVIOR)
# =========================
def engine(price, support, resistance, atr):

    rng = resistance - support

    # 🔥 volatility filter (IMPORTANT FIX)
    volatility_factor = atr / price if price != 0 else 0

    breakout_threshold = resistance * (1 + volatility_factor * 0.5)
    breakdown_threshold = support * (1 - volatility_factor * 0.5)

    breakout = price > breakout_threshold
    breakdown = price < breakdown_threshold

    near_support = price <= support * 1.002
    near_resistance = price >= resistance * 0.998

    score = 40  # base lower than V42 (IMPORTANT FIX)

    reasons = []

    # =========================
    # LOGIC
    # =========================
    if breakout:
        signal = "BREAKOUT"
        direction = "BUY"
        entry = resistance
        sl = support
        tp = resistance + rng
        score += 40
        reasons.append("Volatility breakout detected")

    elif breakdown:
        signal = "BREAKDOWN"
        direction = "SELL"
        entry = support
        sl = resistance
        tp = support - rng
        score += 40
        reasons.append("Volatility breakdown detected")

    elif near_support:
        signal = "SUPPORT REACTION"
        direction = "BUY"
        entry = support
        sl = support - atr
        tp = resistance
        score += 25
        reasons.append("Liquidity at support")

    elif near_resistance:
        signal = "RESISTANCE REJECTION"
        direction = "SELL"
        entry = resistance
        sl = resistance + atr
        tp = support
        score += 25
        reasons.append("Liquidity at resistance")

    else:
        signal = "NO STRUCTURE"
        direction = "WAIT"
        entry = price
        sl = price - atr
        tp = price + atr
        score -= 10
        reasons.append("Market in equilibrium")

    # =========================
    # RR
    # =========================
    risk = abs(entry - sl)
    reward = abs(tp - entry)

    rr = round(reward / risk, 2) if risk != 0 else 0

    # 🔥 RR influence (IMPORTANT FIX)
    if rr > 2:
        score += 15
    elif rr < 1:
        score -= 10

    # randomness removed → stability fixed

    score = max(0, min(100, score))

    return signal, direction, entry, sl, tp, rr, score, reasons

# =========================
# RUN SCAN
# =========================
results = []
charts = {}

for coin in selected:

    df = load_data(coin)

    if df is None or df.empty:
        results.append({
            "Coin": coin,
            "Signal": "NO DATA",
            "Direction": "NONE",
            "Price": None,
            "Entry": None,
            "SL": None,
            "TP": None,
            "RR": 0,
            "Score": 0,
            "Reasons": ["API missing or invalid"]
        })
        continue

    price, support, resistance, atr = structure(df)

    signal, direction, entry, sl, tp, rr, score, reasons = engine(
        price, support, resistance, atr
    )

    charts[coin] = df

    results.append({
        "Coin": coin,
        "Signal": signal,
        "Direction": direction,
        "Price": price,
        "Entry": entry,
        "SL": sl,
        "TP": tp,
        "RR": rr,
        "Score": score,
        "Reasons": reasons
    })

df = pd.DataFrame(results).sort_values("Score", ascending=False)

# =========================
# KPI
# =========================
c1, c2, c3 = st.columns(3)

c1.metric("🟢 BUY", len(df[df["Direction"] == "BUY"]))
c2.metric("🔴 SELL", len(df[df["Direction"] == "SELL"]))
c3.metric("🔥 TOP SCORE", df["Score"].max())

# =========================
# RANKING
# =========================
st.subheader("🏆 V43 MARKET RANKING")

for i, r in df.iterrows():

    cls = "buy" if r["Direction"] == "BUY" else "sell"

    st.markdown(f"""
    <div class="card {cls}">

    <h3>{r['Coin']} – {r['Direction']}</h3>

    <p>{r['Signal']}</p>

    <hr>

    💰 Price: {r['Price']}<br>
    🎯 Entry: {r['Entry']}<br>
    🛑 SL: {r['SL']}<br>
    📈 TP: {r['TP']}<br>

    <hr>

    📊 RR: {r['RR']}<br>
    🧠 Score: {r['Score']}

    </div>
    """, unsafe_allow_html=True)
