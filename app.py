import streamlit as st
import requests
import pandas as pd
import numpy as np

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="V46 ULTRA AI TRADER", layout="wide")

st.title("🤖 V46 ULTRA AI TRADER (CLEAN CORE)")

API_KEY = st.secrets.get("TWELVE_DATA_API_KEY", None)

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh Market"):
    st.cache_data.clear()
    st.rerun()

# =========================
# DARK UI
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

.buy { border-left:5px solid #00FF88; }
.sell { border-left:5px solid #FF3B3B; }

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

    if not API_KEY:
        return None

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
# STRUCTURE ENGINE
# =========================
def structure(df):

    price = df["close"].iloc[-1]

    support = df["low"].rolling(18).min().iloc[-1]
    resistance = df["high"].rolling(18).max().iloc[-1]

    atr = (df["high"] - df["low"]).rolling(18).mean().iloc[-1]

    momentum = df["close"].diff(3).iloc[-1]

    volatility = df["close"].pct_change().std()

    return price, support, resistance, atr, momentum, volatility

# =========================
# V46 AI CORE ENGINE
# =========================
def engine(price, support, resistance, atr, momentum, volatility):

    rng = resistance - support

    score = 50
    reasons = []

    # =========================
    # TREND STRENGTH (FIXED, NO NOISE)
    # =========================
    if momentum > 0:
        score += 12
        reasons.append("Positive momentum trend")
        trend = "BULL"
    else:
        score -= 12
        reasons.append("Negative momentum trend")
        trend = "BEAR"

    # =========================
    # VOLATILITY FILTER (IMPORTANT)
    # =========================
    if volatility < 0.001:
        score -= 10
        reasons.append("Low volatility market")

    # =========================
    # STRUCTURE ZONES
    # =========================
    breakout = price > resistance * 0.999
    breakdown = price < support * 1.001

    near_support = price <= support * 1.002
    near_resistance = price >= resistance * 0.998

    # =========================
    # SIGNAL LOGIC
    # =========================
    if breakout:
        signal = "BREAKOUT BUY"
        direction = "BUY"
        entry = resistance
        sl = support
        tp = resistance + rng
        score += 30
        reasons.append("Breakout above resistance")

    elif breakdown:
        signal = "BREAKDOWN SELL"
        direction = "SELL"
        entry = support
        sl = resistance
        tp = support - rng
        score += 30
        reasons.append("Breakdown below support")

    elif near_support:
        signal = "SUPPORT REACTION"
        direction = "BUY"
        entry = support
        sl = support - atr
        tp = resistance
        score += 18
        reasons.append("Support liquidity zone")

    elif near_resistance:
        signal = "RESISTANCE REJECTION"
        direction = "SELL"
        entry = resistance
        sl = resistance + atr
        tp = support
        score += 18
        reasons.append("Resistance liquidity zone")

    else:
        signal = "NO EDGE"
        direction = "WAIT"
        entry = price
        sl = price - atr
        tp = price + atr
        score -= 8
        reasons.append("No structure detected")

    # =========================
    # RR NORMALIZATION (FIXED STABILITY)
    # =========================
    risk = abs(entry - sl)
    reward = abs(tp - entry)

    rr = round(reward / risk, 2) if risk != 0 else 0

    if rr >= 2:
        score += 12
        reasons.append("Strong risk/reward")
    elif rr < 1.2:
        score -= 10
        reasons.append("Weak risk/reward")

    # =========================
    # FINAL SCORE CLEANUP
    # =========================
    score = max(0, min(100, score))

    return signal, direction, entry, sl, tp, rr, score, reasons, trend

# =========================
# RUN SCAN
# =========================
results = []

for coin in selected:

    df = load_data(coin)

    if df is None or df.empty:
        continue

    price, support, resistance, atr, momentum, volatility = structure(df)

    signal, direction, entry, sl, tp, rr, score, reasons, trend = engine(
        price, support, resistance, atr, momentum, volatility
    )

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
        "Trend": trend,
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
st.subheader("🏆 V46 MARKET RANKING")

for i, r in df.iterrows():

    cls = "buy" if r["Direction"] == "BUY" else "sell"

    st.markdown(f"""
    <div class="card {cls}">

    <h3>{r['Coin']} – {r['Direction']} ({r['Trend']})</h3>

    <p>{r['Signal']}</p>

    <hr>

    💰 Price: {r['Price']}<br>
    🎯 Entry: {r['Entry']}<br>
    🛑 SL: {r['SL']}<br>
    📈 TP: {r['TP']}<br>

    <hr>

    📊 RR: {r['RR']}<br>
    🧠 Score: {r['Score']}

    <hr>

    🧠 AI REASONS:<br>
    {"<br>".join(["- " + x for x in r["Reasons"]])}

    </div>
    """, unsafe_allow_html=True)
