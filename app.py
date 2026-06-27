import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="V42.1 PRO Trading Terminal", layout="wide")

st.title("🚀 V42.1 PRO TRADING TERMINAL")

API_KEY = st.secrets.get("TWELVE_DATA_API_KEY", None)

# =========================
# REFRESH BUTTON
# =========================
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# =========================
# DARK MODE UI
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

.warn {
    color:#FFCC00;
}

</style>
""", unsafe_allow_html=True)

# =========================
# COINS
# =========================
coins = ["BTC/USD","ETH/USD","XRP/USD","SOL/USD","ADA/USD","DOGE/USD","BNB/USD"]

selected = st.sidebar.multiselect("Coins auswählen", coins, default=coins)

# =========================
# SAFE API LOADER (FIX V43 ISSUE)
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
# STRUCTURE
# =========================
def structure(df):
    price = df["close"].iloc[-1]
    support = df["low"].rolling(25).min().iloc[-1]
    resistance = df["high"].rolling(25).max().iloc[-1]
    return price, support, resistance

# =========================
# ENGINE (STABLE)
# =========================
def engine(price, support, resistance):

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

    rr = round(abs(tp-entry)/abs(entry-sl), 2) if entry != sl else 0

    score = 50
    if rr > 2:
        score += 20

    return signal, direction, entry, sl, tp, rr, score

# =========================
# RUN SCAN (NO LOSING COINS)
# =========================
results = []
charts = {}

for coin in selected:

    df = load_data(coin)

    # =========================
    # API FAIL SAFE
    # =========================
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
            "df": None
        })
        continue

    price, support, resistance = structure(df)

    signal, direction, entry, sl, tp, rr, score = engine(
        price, support, resistance
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
        "df": df
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
st.subheader("🏆 MARKET RANKING (ALL COINS)")

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

# =========================
# CANDLE CHARTS (FIXED + CLEAN)
# =========================
st.subheader("📉 CANDLE VIEW (15M – LIVE STYLE)")

for coin in selected:

    dfc = charts.get(coin)

    if dfc is None:
        st.warning(f"{coin} – keine Daten")
        continue

    dfc = dfc.tail(80)

    fig = go.Figure(data=[
        go.Candlestick(
            open=dfc["open"],
            high=dfc["high"],
            low=dfc["low"],
            close=dfc["close"],
            name=coin
        )
    ])

    fig.update_layout(
        height=300,
        paper_bgcolor="#05070D",
        plot_bgcolor="#05070D",
        margin=dict(l=10, r=10, t=20, b=10)
    )

    st.caption(coin)
    st.plotly_chart(fig, use_container_width=True)
