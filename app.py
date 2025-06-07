import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import date

st.set_page_config(page_title="Stock Dashboard", layout="wide", initial_sidebar_state="expanded")

@st.cache_data(show_spinner=False)
def fetch_ohlcv(tickers, start_date, end_date):
    return yf.download(tickers=tickers, start=start_date, end=end_date, progress=False)

st.sidebar.header("🔧 Configuration")

default_tickers = ["MSFT", "GE", "AAPL"]
all_choices = st.sidebar.text_input("Enter tickers (comma-separated)", value=",".join(default_tickers))
tickers = [s.strip().upper() for s in all_choices.split(",") if s.strip()]

today = date.today()
c1, c2 = st.sidebar.columns(2)
with c1:
    start_date = st.date_input("Start Date", value=date(2010,1,1))
with c2:
    end_date = st.date_input("End Date", value=today)
if start_date >= end_date:
    st.sidebar.error("⚠️ Start date must be before end date.")

price_field = st.sidebar.selectbox("Price Field", ["Open","High","Low","Close","Adj Close","Volume"], index=3)
frequency   = st.sidebar.selectbox("Frequency", ["Daily","Weekly","Monthly"], index=0)
normalize   = st.sidebar.checkbox("Normalize to 100", value=False)

st.sidebar.markdown("---")
st.sidebar.markdown("**Moving Average 1**")
ma1_enabled = st.sidebar.checkbox("Enable MA1", value=False)
ma1_window  = st.sidebar.slider("MA1 Window (days)", 2, 200, 20)

st.sidebar.markdown("**Moving Average 2**")
ma2_enabled = st.sidebar.checkbox("Enable MA2", value=False)
ma2_window  = st.sidebar.slider("MA2 Window (days)", 2, 200, 50)

if not tickers:
    st.error("❌ Please enter at least one ticker symbol.")
    st.stop()

with st.spinner("Fetching data..."):
    df_full = fetch_ohlcv(tickers, start_date, end_date)
    if df_full.empty:
        st.error("⚠️ No data returned. Check symbols or date range.")
        st.stop()

if price_field not in df_full.columns.levels[0]:
    st.error(f"⚠️ '{price_field}' field not available.")
    st.stop()

df_price = df_full[price_field].copy()

if frequency == "Daily":
    df_resampled = df_price;        freq_suffix = " (Daily)"
elif frequency == "Weekly":
    df_resampled = df_price.resample("W").last(); freq_suffix = " (Weekly)"
else:
    df_resampled = df_price.resample("M").last(); freq_suffix = " (Monthly)"

df_resampled = df_resampled.dropna(axis=1, how="all")
if df_resampled.empty:
    st.error("❌ After resampling, no data remains.")
    st.stop()

if normalize:
    df_norm = pd.DataFrame(index=df_resampled.index)
    for col in df_resampled.columns:
        s = df_resampled[col].dropna()
        df_norm[col] = (df_resampled[col]/s.iloc[0])*100 if not s.empty and s.iloc[0]!=0 else np.nan
    df_to_plot = df_norm; norm_suffix = " (Normalized → 100)"
else:
    df_to_plot = df_resampled; norm_suffix = ""

dropped = [t for t in tickers if t not in df_to_plot.columns]
if dropped:
    st.warning(f"⚠️ Dropped (no data): {', '.join(dropped)}")

fig = go.Figure()
for ticker in df_to_plot.columns:
    fig.add_trace(go.Scatter(x=df_to_plot.index, y=df_to_plot[ticker],
                             mode="lines", name=ticker, line=dict(width=2)))
if ma1_enabled:
    for ticker in df_to_plot.columns:
        ma = df_to_plot[ticker].rolling(ma1_window).mean()
        fig.add_trace(go.Scatter(x=ma.index, y=ma, mode="lines",
                                 name=f"{ticker} MA{ma1_window}", line=dict(width=1,dash="dash")))
if ma2_enabled:
    for ticker in df_to_plot.columns:
        ma2 = df_to_plot[ticker].rolling(ma2_window).mean()
        fig.add_trace(go.Scatter(x=ma2.index, y=ma2, mode="lines",
                                 name=f"{ticker} MA{ma2_window}", line=dict(width=1,dash="dot")))

fig.update_layout(
    title=dict(text=f"{', '.join(df_to_plot.columns)} | {price_field}{freq_suffix}{norm_suffix}", x=0.5),
    xaxis=dict(title="Date", rangeslider=dict(visible=True), type="date"),
    yaxis=dict(title="Price"+(" (Normalized)" if normalize else " (USD)")),
    legend=dict(orientation="h", y=1.02, x=1),
    margin=dict(l=50,r=50,t=80,b=50), height=600, template="plotly_white"
)

st.plotly_chart(fig, use_container_width=True)
with st.expander("Show data table"):
    st.dataframe(df_to_plot)
st.markdown("---\nBuilt with [Streamlit](https://streamlit.io) • Data via [yfinance](https://github.com/ranaroussi/yfinance)\n")
