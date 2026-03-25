"""
10-Bagger v2 — 貝葉斯分析頁
Bayesian probability tracking, debate results, and update detail.
"""

import streamlit as st
import pandas as pd

from utils.supabase_client import (
    fetch_active_stocks,
    fetch_stock_probabilities,
    fetch_probability_log,
    fetch_evidence_log,
)
from utils.charts import probability_gauge, probability_history_line, evidence_timeline
from utils.constants import PH_ELIMINATION, PH_HIGH_PROBABILITY, ALERT_LABELS

st.set_page_config(page_title="貝葉斯分析 | 10-Bagger", page_icon="🧪", layout="wide")
st.markdown("## 🧪 貝葉斯分析")

# ── Data ──────────────────────────────────────────────────────
stocks = fetch_active_stocks()
probs = fetch_stock_probabilities()
prob_map = {p["stock_ticker"]: p for p in probs}

if not stocks:
    st.warning("尚無追蹤股票。")
    st.stop()

# ── Overview: all-stock P(H) comparison ───────────────────────
st.markdown("### 📊 全股票 P(H) 比較")

sorted_probs = sorted(probs, key=lambda p: p.get("current_ph", 0), reverse=True)
cols_per_row = 4
for i in range(0, len(sorted_probs), cols_per_row):
    row = sorted_probs[i : i + cols_per_row]
    cols = st.columns(cols_per_row)
    for idx, p in enumerate(row):
        with cols[idx]:
            fig = probability_gauge(p["stock_ticker"], p.get("current_ph", 0.15))
            st.plotly_chart(fig, use_container_width=True, key=f"ba_gauge_{p['stock_ticker']}")
            updates = p.get("total_updates", 0)
            st.caption(f"更新 {updates} 次")

st.divider()

# ── P(H) History — all stocks ─────────────────────────────────
st.markdown("### 📈 全股票 P(H) 歷史走勢")

all_log = fetch_probability_log(limit=500)
if all_log:
    df_all = pd.DataFrame(all_log)
    df_all["created_at"] = pd.to_datetime(df_all["created_at"])
    fig_all = probability_history_line(df_all)
    st.plotly_chart(fig_all, use_container_width=True)
else:
    st.info("尚無 P(H) 更新記錄。")

st.divider()

# ── Per-stock deep dive ───────────────────────────────────────
st.markdown("### 🔬 個股貝葉斯更新明細")

tickers = [s["ticker"] for s in stocks]
selected = st.selectbox("選擇股票", tickers, index=0, key="ba_stock_select")

prob_info = prob_map.get(selected, {})
current_ph = prob_info.get("current_ph", 0.15)

# Alert
col_alert, col_stat = st.columns([2, 1])
with col_alert:
    if current_ph < PH_ELIMINATION:
        st.error(f"⚠️ {selected} 低於淘汰線 ({current_ph:.1%} < 5%)")
    elif current_ph >= PH_HIGH_PROBABILITY:
        st.success(f"🔥 {selected} 為高機率十倍股候選 ({current_ph:.1%})")
    else:
        st.info(f"📈 {selected} 目前 P(H) = {current_ph:.1%}")
with col_stat:
    st.metric("累計更新次數", prob_info.get("total_updates", 0))

# Per-stock history chart
stock_log = fetch_probability_log(selected, limit=100)
if stock_log:
    df_stock = pd.DataFrame(stock_log)
    df_stock["created_at"] = pd.to_datetime(df_stock["created_at"])
    fig_stock = probability_history_line(df_stock, selected)
    st.plotly_chart(fig_stock, use_container_width=True)

    # Update detail table
    st.markdown("#### 📋 更新明細")
    for entry in stock_log[:10]:
        alert = entry.get("alert_type", "none")
        label, color = ALERT_LABELS.get(alert, ("—", "gray"))
        prior = entry.get("prior_ph", 0)
        new = entry.get("new_ph", 0)
        delta = new - prior

        icon = "🔴" if "low" in alert else "🟢" if "high" in alert else "⚪"
        with st.expander(
            f"{icon} {entry.get('created_at', '')[:16]} — "
            f"P(H) {prior:.2%} → {new:.2%} "
            f"({'▲' if delta > 0 else '▼'} {abs(delta):.2%})"
        ):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**📈 Bull Case**")
                st.markdown(f"P(E|H): {entry.get('pe_h_bull', 0):.3f}")
                st.markdown(f"P(E|¬H): {entry.get('pe_not_h_bull', 0):.3f}")
            with c2:
                st.markdown("**📉 Bear Case**")
                st.markdown(f"P(E|H): {entry.get('pe_h_bear', 0):.3f}")
                st.markdown(f"P(E|¬H): {entry.get('pe_not_h_bear', 0):.3f}")
            with c3:
                st.markdown("**⚖️ Final (Judge)**")
                st.markdown(f"P(E|H): {entry.get('final_pe_h', 0):.3f}")
                st.markdown(f"P(E|¬H): {entry.get('final_pe_not_h', 0):.3f}")

            st.markdown(f"**信心度：** {entry.get('confidence', 0):.0%}")
            st.markdown(f"**警報：** {label}")

            if entry.get("judge_ruling"):
                st.markdown("---")
                st.markdown(f"**裁判裁定：** {entry['judge_ruling'][:500]}")
else:
    st.info(f"{selected} 尚無貝葉斯更新記錄。")

st.divider()

# ── Evidence timeline ─────────────────────────────────────────
st.markdown("### 🕐 證據收集時間軸")

evidence = fetch_evidence_log(selected, limit=50)
if evidence:
    df_ev = pd.DataFrame(evidence)
    df_ev["created_at"] = pd.to_datetime(df_ev["created_at"])
    fig_ev = evidence_timeline(df_ev)
    st.plotly_chart(fig_ev, use_container_width=True)

    st.markdown("#### 最近證據")
    for ev in evidence[:5]:
        with st.expander(f"📌 {ev.get('created_at', '')[:16]} — {ev.get('source_type', '')}"):
            st.markdown(f"**來源：** {ev.get('source_url', '—')}")
            st.markdown(f"**摘要：** {ev.get('summary', '—')}")
            if ev.get("key_findings"):
                st.markdown(f"**關鍵發現：** {ev['key_findings']}")
else:
    st.info(f"{selected} 尚無證據記錄。")
