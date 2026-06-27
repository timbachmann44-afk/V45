import streamlit as st
import requests
import pandas as pd
import numpy as np

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="V42 Trading Terminal", layout="wide")

st.title("🚀 V42 VISUAL TRADING TERMINAL")

API_KEY = st.secrets["TWELVE_DATA_API_KEY"]

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

# =========================
# DARK UI + VISUAL RESET
# =========================
st.markdown("""
<style>

.stApp {
    background:#05070D;
    color:#EAEAEA;
}

/* GRID LAYOUT */
.grid {
    display:grid;
    grid-template-columns: repeat(2, 1fr);
    gap:16px;
}

/* CARD BASE */
.card {
    background: linear-gradient(145deg, #0B1220, #0F172A);
    padding:16px;
    border-radius:16px;
    border:1px solid #1f2937;
    box-shadow:0px 0px 18px rgba(0,0,0,0.6);
    margin-bottom:12px;
}

/* BUY STYLE */
.buy {
    border-left:6px solid #00ff88;
    box-shadow:0px 0px 25px rgba(0,255,136,0.18);
}

/* SELL STYLE */
.sell {
    border-left:6px solid #ff3b3b;
    box-shadow:0px 0px 25px rgba(255,59,59,0.18);
}

/* TEXT */
h1,h2,h3 {
    color:#00E5FF;
}

.small {
    font-size:12px;
    opacity:0.6;
}

</style>
""", unsafe_allow_html=True)

# =========================
# COINS
# =========================
coins = ["BTC/USD","ETH/USD","XRP/USD","SOL/USD","ADA/USD","DOGE/USD","BNB/USD"]

selected = st.sidebar.multiselect("Coins", coins, default=coins)

# =========================
# DATA
# =========================
@st.cache_data(ttl=30)
def load_data(symbol):

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": symbol,
        "interval": "15min",
        "outputsize": 200,
        "apikey": API_KEY
    }

    r = requests.get(url, params=params).json()

    if "values" not in r:
        return None

    df = pd.DataFrame(r["values"])
    df = df.iloc[::-1]

    for c in ["open","high","low","close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

# =========================
# AI ENGINE (CLEAN + STABLE)
# =========================
def analyze(df):

    price = df["close"].iloc[-1]

    support = df["low"].rolling(25).min().iloc[-1]
    resistance = df["high"].rolling(25).max().iloc[-1]

    ema20 = df["close"].ewm(span=20).mean().iloc[-1]
    ema50 = df["close"].ewm(span=50).mean().iloc[-1]

    trend = "BULL" if ema20 > ema50 else "BEAR"

    rng = resistance - support

    breakout = price > resistance
    breakdown = price < support

    if breakout:
        direction = "BUY"
        signal = "BREAKOUT"
        entry = resistance
        sl = support
        tp = resistance + rng
    elif breakdown:
        direction = "SELL"
        signal = "BREAKDOWN"
        entry = support
        sl = resistance
        tp = support - rng
    else:
        direction = "WAIT"
        signal = "RANGE"
        entry = price
        sl = price * 0.98
        tp = price * 1.02

    risk = abs(entry - sl)
    reward = abs(tp - entry)

    rr = round(reward / risk, 2) if risk != 0 else 0

    score = 50

    if trend == "BULL":
        score += 20
    else:
        score -= 10

    if rr > 2:
        score += 10

    return {
        "coin": None,
        "price": price,
        "support": support,
        "resistance": resistance,
        "ema20": ema20,
        "ema50": ema50,
        "trend": trend,
        "direction": direction,
        "signal": signal,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "rr": rr,
        "score": score,
        "df": df
    }

# =========================
# RUN SCAN
# =========================
results = []
data_map = {}

for coin in selected:

    df = load_data(coin)
    if df is None:
        continue

    res = analyze(df)
    res["coin"] = coin

    results.append(res)
    data_map[coin] = res

df = pd.DataFrame(results)

if df.empty:
    st.warning("Keine Daten verfügbar")
    st.stop()

df = df.sort_values("score", ascending=False).reset_index(drop=True)

# =========================
# HEADER METRICS
# =========================
c1, c2, c3 = st.columns(3)

c1.metric("🟢 BUY", len(df[df["direction"] == "BUY"]))
c2.metric("🔴 SELL", len(df[df["direction"] == "SELL"]))
c3.metric("🔥 TOP SCORE", df["score"].max())

# =========================
# GRID VISUAL DASHBOARD (BIG CHANGE)
# =========================
st.subheader("📊 VISUAL TRADING GRID")

cols = st.columns(2)

for i, r in df.iterrows():

    cls = "buy" if r["direction"] == "BUY" else "sell"

    with cols[i % 2]:

        st.markdown(f"""
        <div class="card {cls}">

        <h3>{r['coin']} – {r['direction']}</h3>

        <div class="small">{r['signal']} | Trend: {r['trend']}</div>

        <hr>

        💰 Price: <b>{r['price']}</b><br>
        🎯 Entry: <b>{r['entry']}</b><br>
        🛑 Stop: <b>{r['sl']}</b><br>
        📈 TP: <b>{r['tp']}</b><br>

        <hr>

        📊 RR: <b>{r['rr']}</b><br>
        🧠 Score: <b>{r['score']}</b>

        </div>
        """, unsafe_allow_html=True)

# =========================
# BEST SETUP
# =========================
best = df.iloc[0]

st.success(f"""
🏆 BEST SETUP

Coin: {best['coin']}
Direction: {best['direction']}
Signal: {best['signal']}
Score: {best['score']}
RR: {best['rr']}
""")