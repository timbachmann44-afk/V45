import streamlit as st
import requests
import pandas as pd
import numpy as np

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="V51.1 AI TRADER", layout="wide")

st.title("🚀 V51.1 LONG / SHORT AI TRADER")

API_KEY = st.secrets.get("TWELVE_DATA_API_KEY", None)

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh Engine"):
    st.cache_data.clear()
    st.rerun()

# =========================
# UI STYLE
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

</style>
""", unsafe_allow_html=True)

# =========================
# COINS
# =========================
coins = ["BTC/USD","ETH/USD","XRP/USD","SOL/USD","ADA/USD","DOGE/USD","BNB/USD"]

selected = st.sidebar.multiselect("Coins", coins, default=coins)

# =========================
# SAFE DATA LOADER
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

    if df is None or len(df) < 30:
        return None, None, None, None, None

    price = df["close"].iloc[-1]
    support = df["low"].rolling(20).min().iloc[-1]
    resistance = df["high"].rolling(20).max().iloc[-1]
    atr = (df["high"] - df["low"]).rolling(20).mean().iloc[-1]
    momentum = df["close"].diff(5).mean()

    return price, support, resistance, atr, momentum

# =========================
# LONG / SHORT ENTRY ZONES (NEW)
# =========================
def entry_zone_lr(price, support, resistance, atr):

    zone_size = atr * 0.6

    long_low = support
    long_high = support + zone_size

    short_low = resistance - zone_size
    short_high = resistance

    if long_low <= price <= long_high:
        return "LONG_ZONE", long_low, long_high

    elif short_low <= price <= short_high:
        return "SHORT_ZONE", short_low, short_high

    else:
        return "NO_ZONE", None, None

# =========================
# ENGINE
# =========================
def engine(price, support, resistance, atr, momentum, zone):

    if None in [price, support, resistance, atr]:
        return "NO DATA", "WAIT", None, None, None, 0, 0, ["Missing data"]

    score = 50
    reasons = []

    rng = resistance - support

    # MOMENTUM
    direction = "NONE"

    if momentum > 0:
        score += 10
        direction = "BUY"
        reasons.append("Bullish momentum")
    else:
        score -= 10
        direction = "SELL"
        reasons.append("Bearish momentum")

    # =========================
    # ZONE LOGIC
    # =========================
    if zone == "LONG_ZONE":
        signal = "LONG SETUP"
        entry_low = support
        entry_high = support + atr
        sl = support - atr
        tp = resistance
        score += 25
        reasons.append("Long zone active")

    elif zone == "SHORT_ZONE":
        signal = "SHORT SETUP"
        entry_low = resistance - atr
        entry_high = resistance
        sl = resistance + atr
        tp = support
        score += 25
        reasons.append("Short zone active")

    else:
        signal = "WAIT"
        entry_low = None
        entry_high = None
        sl = None
        tp = None
        score -= 20
        reasons.append("No valid entry zone")

    # =========================
    # RR CALCULATION
    # =========================
    rr = 0

    if entry_low is not None:
        entry = (entry_low + entry_high) / 2
        risk = abs(entry - sl)
        reward = abs(tp - entry)

        rr = round(reward / risk, 2) if risk != 0 else 0

        if rr > 2:
            score += 10
        elif rr < 1.2:
            score -= 10

    score = max(0, min(100, score))

    return signal, direction, entry_low, entry_high, sl, tp, rr, score, reasons

# =========================
# RUN SCAN
# =========================
results = []

for coin in selected:

    df = load_data(coin)

    price, support, resistance, atr, momentum = structure(df)

    zone, zlow, zhigh = entry_zone_lr(price, support, resistance, atr)

    signal, direction, e_low, e_high, sl, tp, rr, score, reasons = engine(
        price, support, resistance, atr, momentum, zone
    )

    results.append({
        "Coin": coin,
        "Signal": signal,
        "Direction": direction,
        "Zone": zone,
        "Entry Zone": f"{round(e_low,2) if e_low else None} - {round(e_high,2) if e_high else None}",
        "SL": round(sl,2) if sl else None,
        "TP": round(tp,2) if tp else None,
        "RR": rr,
        "Score": score,
        "Reasons": reasons
    })

df = pd.DataFrame(results)

# =========================
# SAFE CHECK
# =========================
if df.empty:
    st.error("No data available")
    st.stop()

df = df.sort_values("Score", ascending=False)

# =========================
# KPI
# =========================
c1, c2, c3 = st.columns(3)

c1.metric("🟢 LONG", len(df[df["Zone"] == "LONG_ZONE"]))
c2.metric("🔴 SHORT", len(df[df["Zone"] == "SHORT_ZONE"]))
c3.metric("⚪ NO ZONE", len(df[df["Zone"] == "NO_ZONE"]))

# =========================
# TOP TRADE
# =========================
best = df.iloc[0]

st.success(f"""
🏆 BEST SETUP

Coin: {best['Coin']}
Signal: {best['Signal']}
Zone: {best['Zone']}
Score: {best['Score']}
RR: {best['RR']}
""")

# =========================
# RANKING
# =========================
st.subheader("🚀 V51.1 AI RANKING (LONG / SHORT ZONES)")

for _, r in df.iterrows():

    st.markdown(f"""
    <div class="card">

    <h3>{r['Coin']} – {r['Signal']}</h3>

    📍 Zone: {r['Zone']}<br>
    📊 Direction: {r['Direction']}<br>

    <hr>

    🎯 Entry Zone: {r['Entry Zone']}<br>
    🛑 SL: {r['SL']}<br>
    📈 TP: {r['TP']}<br>

    <hr>

    📊 RR: {r['RR']}<br>
    🧠 Score: {r['Score']}

    <hr>

    🧠 AI:
    {"<br>".join(["- " + x for x in r["Reasons"]])}

    </div>
    """, unsafe_allow_html=True)
