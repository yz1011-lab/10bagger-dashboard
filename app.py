"""
10-Bagger Agent System — 戰情儀表板 v2
Main entry: Dashboard Overview
"""

import streamlit as st
import pandas as pd

from utils.supabase_client import (
    fetch_active_stocks,
    fetch_stock_probabilities,
    fetch_probability_log,
    fetch_tracks,
    fetch_evidence_log,
)
from utils.charts import (
    probability_gauge,
    probability_history_line,
    track_confidence_bar,
)
from utils.constants import PH_ELIMINATION, PH_HIGH_PROBABILITY, ALERT_LABELS

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="10-Bagger 戰情儀表板",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.image("https://em-content.zobj.net/source/twitter/376/direct-hit_1f3af.png", width=48)
    st.title("10-Bagger v2")
    st.caption("Multi-Agent 股票分析系統")
    st.divider()
    if st.button("🔄 重新整理資料", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Load data ────────────────────────────────────────────────
stocks = fetch_active_stocks()
probs = fetch_stock_probabilities()
tracks = fetch_tracks()

prob_map: dict[str, float] = {p["stock_ticker"]: p["current_ph"] for p in probs}
total_updates_map: dict[str, int] = {p["stock_ticker"]: p.get("total_updates", 0) for p in probs}

# ── Header KPIs ──────────────────────────────────────────────
st.markdown("## 🎯 戰情總覽")

col1, col2, col3, col4, col5 = st.columns(5)
n_stocks = len(stocks)
n_high = sum(1 for v in prob_map.values() if v >= PH_HIGH_PROBABILITY)
n_low = sum(1 for v in prob_map.values() if v < PH_ELIMINATION)
n_tracks = len(tracks)
total_evidence = sum(total_updates_map.values())

col1.metric("追蹤股票", n_stocks)
col2.metric("🔥 高機率候選", n_high)
col3.metric("⚠️ 低機率警示", n_low)
col4.metric("賽道數量", n_tracks)
col5.metric("累計貝葉斯更新", total_evidence)

st.divider()

# ── Probability gauges ───────────────────────────────────────
st.markdown("### 📊 各股 P(H) 儀表板")

if probs:
    cols_per_row = 4
    rows = [probs[i : i + cols_per_row] for i in range(0, len(probs), cols_per_row)]
    for row_data in rows:
        cols = st.columns(cols_per_row)
        for idx, p in enumerate(row_data):
            with cols[idx]:
                fig = probability_gauge(p["stock_ticker"], p["current_ph"])
                st.plotly_chart(fig, use_container_width=True, key=f"gauge_{p['stock_ticker']}")
                updates = p.get("total_updates", 0)
                st.caption(f"更新 {updates} 次")
else:
    st.info("尚無股票機率資料。請先執行 Bayesian Analyst Agent。")

st.divider()

# ── P(H) history line chart ──────────────────────────────────
st.markdown("### 📈 P(H) 歷史走勢")

log_data = fetch_probability_log(limit=500)
if log_data:
    df_log = pd.DataFrame(log_data)
    df_log["created_at"] = pd.to_datetime(df_log["created_at"])
    fig_line = probability_history_line(df_log)
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("尚無更新記錄。")

st.divider()

# ── Tracks ───────────────────────────────────────────────────
st.markdown("### 🛤️ 賽道信心指數")

col_chart, col_table = st.columns([2, 1])
with col_chart:
    fig_tracks = track_confidence_bar(tracks)
    st.plotly_chart(fig_tracks, use_container_width=True)
with col_table:
    if tracks:
        for t in tracks:
            consensus = t.get("consensus_level", "moderate")
            emoji = {"high": "🟢", "moderate": "🟡", "contrarian": "🔴"}.get(consensus, "⚪")
            st.markdown(f"**{emoji} {t['name']}**  \n信心 {t.get('confidence', 0):.0f}% · 共識 {consensus}")
    else:
        st.info("尚無賽道資料。")

st.divider()

# ── Stock table ──────────────────────────────────────────────
st.markdown("### 📋 追蹤股票清單")

if stocks:
    table_rows = []
    for s in stocks:
        ticker = s.get("ticker", "")
        ph = prob_map.get(ticker, None)
        table_rows.append({
            "股票代碼": ticker,
            "名稱": s.get("name", ""),
            "市場": s.get("market", ""),
            "P(H)": f"{ph:.1%}" if ph is not None else "—",
            "狀態": s.get("status", ""),
            "更新次數": total_updates_map.get(ticker, 0),
        })
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
else:
    st.info("尚無追蹤股票。")

# ── Footer ───────────────────────────────────────────────────
st.divider()
st.caption("10-Bagger Agent System v2 · Powered by n8n + Supabase + Claude · 戰情儀表板")
